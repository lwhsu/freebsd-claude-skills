# VuXML Entry Format

VuXML entries are added to `security/vuxml/vuln.xml`.

## Template

```xml
  <vuln vid="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX">
    <topic>Product -- short vulnerability description</topic>
    <body xmlns="http://www.w3.org/1999/xhtml">
      <p>The vendor reports:</p>
      <blockquote cite="https://advisory-url">
        <p>Description of the vulnerability from the advisory.</p>
      </blockquote>
    </body>
    <references>
      <cvename>CVE-YYYY-NNNNN</cvename>
      <url>https://advisory-url</url>
    </references>
    <dates>
      <discovery>YYYY-MM-DD</discovery>
      <entry>YYYY-MM-DD</entry>
    </dates>
    <affects>
      <package>
        <name>portname</name>
        <range><lt>fixed-version</lt></range>
      </package>
    </affects>
  </vuln>
```

## Field descriptions

- **vid**: A unique UUID. Generate with `uuidgen`.
- **topic**: Short one-line description. Format: `Product -- vulnerability summary`
- **body**: Detailed description, typically quoting the upstream advisory.
- **references**: CVE IDs and advisory URLs.
  - Use `<cvename>` for CVE IDs
  - Use `<url>` for advisory URLs
  - Use `<bid>` for SecurityFocus BIDs (rare)
- **dates**:
  - `discovery`: When the vulnerability was discovered/disclosed
  - `entry`: Today's date (when the VuXML entry is created)
- **affects**: Package names and vulnerable version ranges.
  - `<lt>`: Less than (versions below the fix)
  - `<le>`: Less than or equal
  - `<gt>`: Greater than
  - `<ge>`: Greater than or equal
  - `<eq>`: Equal to
  - `<range>` can combine elements: `<ge>1.0</ge><lt>1.5.2</lt>`

## Multiple packages

If the vulnerability affects multiple ports (e.g., a package with `-lts` variant):

```xml
    <affects>
      <package>
        <name>portname</name>
        <range><lt>2.0.1</lt></range>
      </package>
      <package>
        <name>portname-lts</name>
        <range><ge>1.0</ge><lt>1.8.5</lt></range>
      </package>
    </affects>
```

## Placement

New entries should be added near the top of `vuln.xml`, after the opening `<vuxml>` tag and any existing recent entries. Follow the chronological ordering used in the file.

## Commit message

```
security/vuxml: Document <Product> Security Advisory YYYY-MM-DD
```
