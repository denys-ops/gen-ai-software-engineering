# File Import Format Specifications

## CSV Format

UTF-8 encoded, RFC 4180-compliant. A header row is required.

**Required columns:** `customer_id`, `customer_email`, `customer_name`, `subject`, `description`

**Optional columns:** `category`, `priority`, `status`, `assigned_to`, `tags`, `metadata_source`, `metadata_browser`, `metadata_device_type`

**Rules:**
- Unknown column names → 400 at the container level.
- Blank cells are treated as the field being omitted (model defaults apply).
- `tags`: semicolon-separated (`login;urgent`). Empty or whitespace-only → `[]`.
- `metadata_*` columns: if any of the three is non-blank, a `TicketMetadata` object is constructed; otherwise `metadata = null`.
- Row 1 = first data row (the row immediately after the header).

**Example:**

```
customer_id,customer_email,customer_name,subject,description,category,priority,status,assigned_to,tags,metadata_source,metadata_browser,metadata_device_type
CUST-001,alice@example.com,Alice Example,Cannot log in,I cannot log into my account since yesterday.,account_access,high,new,,login;urgent,web_form,Chrome,desktop
CUST-002,bob@example.com,Bob Example,Invoice question,I have a question about invoice number 12345.,billing_question,medium,new,agent-7,billing,email,,
```

---

## JSON Format

Top-level value must be an array. Each element is a `TicketCreate` object (same fields and constraints as `POST /tickets` body).

**Rules:**
- Non-array top-level value → 400.
- Non-object array elements → per-row `ImportError` in `ImportSummary`.
- Row 1 = first array element.

**Example:**

```json
[
  {
    "customer_id": "CUST-001",
    "customer_email": "alice@example.com",
    "customer_name": "Alice Example",
    "subject": "Cannot log in",
    "description": "I cannot log into my account since yesterday.",
    "category": "account_access",
    "priority": "high",
    "tags": ["login", "urgent"],
    "metadata": {"source": "web_form", "browser": "Chrome", "device_type": "desktop"}
  },
  {
    "customer_id": "CUST-002",
    "customer_email": "bob@example.com",
    "customer_name": "Bob Example",
    "subject": "Invoice question",
    "description": "I have a question about invoice number 12345."
  }
]
```

---

## XML Format

Root element `<tickets>`, child elements `<ticket>`. Each scalar field is a child element whose tag name matches the JSON key (snake_case). Tags use `<tags><tag>` wrapper; metadata uses `<metadata>` with `<source>`, `<browser>`, `<device_type>` children. Parsed with `defusedxml.ElementTree` (secure; never stdlib `xml.etree`).

**Rules:**
- All values are element text content (no XML attributes).
- Optional fields may be omitted entirely; empty text content is treated as omission.
- Whitespace surrounding element text is stripped.
- Row 1 = first `<ticket>` element.

**Example:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tickets>
  <ticket>
    <customer_id>CUST-001</customer_id>
    <customer_email>alice@example.com</customer_email>
    <customer_name>Alice Example</customer_name>
    <subject>Cannot log in</subject>
    <description>I cannot log into my account since yesterday.</description>
    <category>account_access</category>
    <priority>high</priority>
    <status>new</status>
    <assigned_to></assigned_to>
    <tags>
      <tag>login</tag>
      <tag>urgent</tag>
    </tags>
    <metadata>
      <source>web_form</source>
      <browser>Chrome</browser>
      <device_type>desktop</device_type>
    </metadata>
  </ticket>
  <ticket>
    <customer_id>CUST-002</customer_id>
    <customer_email>bob@example.com</customer_email>
    <customer_name>Bob Example</customer_name>
    <subject>Invoice question</subject>
    <description>I have a question about invoice number 12345.</description>
  </ticket>
</tickets>
```
