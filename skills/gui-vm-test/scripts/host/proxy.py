#!/usr/bin/env python3
# Minimal HTTP proxy (CONNECT and absolute-URI GET) for guests on a host-only
# switch, for hosts that do not NAT the guest network.
#
# usage: proxy.py <bind-address> <port> [allowed-suffix ...]   (default: freebsd.org)
#
# Limits: binds to one address; host names must be plain DNS names under an
# allowed suffix; CONNECT only to port 443 and GET only to port 80; the
# resolved address must be a public one.  Any client that can reach the bind
# address can use it, so stop it when the test is done.
import ipaddress
import re
import select
import socket
import sys
import threading

BIND, PORT = sys.argv[1], int(sys.argv[2])
ALLOW = tuple(a.lower().strip('.') for a in sys.argv[3:]) or ('freebsd.org',)
NAME = re.compile(r'[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*')


def connect(host, port, want):
    host = host.lower().rstrip('.')
    if not NAME.fullmatch(host) or len(host) > 253:
        raise Exception('bad host name %r' % host)
    if not any(host == a or host.endswith('.' + a) for a in ALLOW):
        raise Exception('denied ' + host)
    if port != want:
        raise Exception('denied port %d for %s' % (port, host))
    last = None
    for fam, typ, proto, _, addr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[0]).is_global:
            last = Exception('denied address %s for %s' % (addr[0], host))
            continue
        s = socket.socket(fam, typ, proto)
        s.settimeout(30)
        try:
            s.connect(addr)
            s.settimeout(None)
            return s
        except OSError as e:
            s.close()
            last = e
    raise last or Exception('no address for ' + host)


def pipe(a, b):
    socks = [a, b]
    try:
        while True:
            r, _, _ = select.select(socks, [], [], 300)
            if not r:
                return
            for s in r:
                d = s.recv(65536)
                if not d:
                    return
                (b if s is a else a).sendall(d)
    finally:
        a.close()
        b.close()


def handle(c):
    u = None
    try:
        buf = b''
        while b'\r\n\r\n' not in buf:
            d = c.recv(65536)
            if not d or len(buf) > 65536:
                c.close()
                return
            buf += d
        head, rest = buf.split(b'\r\n\r\n', 1)
        lines = head.split(b'\r\n')
        meth, url, ver = lines[0].split(b' ', 2)
        if meth == b'CONNECT':
            host, port = url.decode('ascii').rsplit(':', 1)
            u = connect(host, int(port), 443)
            c.sendall(b'HTTP/1.1 200 Connection established\r\n\r\n')
            if rest:
                u.sendall(rest)
        else:
            u_ = url.decode('ascii')
            if not u_.startswith('http://'):
                raise Exception('bad request')
            hp, _, path = u_[7:].partition('/')
            host, _, port = hp.partition(':')
            u = connect(host, int(port or 80), 80)
            # One request per connection: later requests on a kept-alive
            # connection would not be checked.
            out = [meth + b' /' + path.encode('ascii') + b' ' + ver]
            out += [l for l in lines[1:]
                    if not l.lower().startswith((b'proxy-', b'connection:'))]
            out.append(b'Connection: close')
            u.sendall(b'\r\n'.join(out) + b'\r\n\r\n' + rest)
        print('ok', lines[0].decode('ascii', 'replace'), flush=True)
        pipe(c, u)
    except Exception as e:
        print('err', e, flush=True)
        try:
            c.sendall(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
        except Exception:
            pass
        for s in (c, u):
            try:
                if s:
                    s.close()
            except Exception:
                pass


s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((BIND, PORT))
s.listen(64)
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
