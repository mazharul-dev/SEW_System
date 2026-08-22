# Smart Employee Working System

A unified Flask dashboard for Bangla content conversion, MCQ proofreading, DOCX cleanup, and question formatting. The project brings several employee productivity tools together behind one browser-based workspace with email-based join requests and administrator approval.

## What It Includes

| Tool | Purpose |
| --- | --- |
| **Bangla Convert** | Convert Bangla text between Unicode and Bijoy formats. |
| **Model Test Book Generate** | Clean exam DOCX files, remove solution or answer sections, apply OMR-style options, and generate a two-column document. |
| **Question Repeat Checker** | Parse table-based MCQs, identify repeated questions, and review spelling. |
| **Table Based Convert** | Convert unstructured MCQ DOCX content into a structured table format. |
| **In-Branch Question Convert** | Convert Unicode/Avro Bangla DOCX questions into Bijoy SutonnyMJ DOCX files while preserving Word equations and images. |

## Key Features

- Single dashboard for all integrated tools
- Email join-request workflow with administrator approval and revocation
- DOCX upload and download support
- In-memory processing for the proofreader workflow
- LanguageTool-backed English spell checking and local Bangla wordlist support
- Preservation of Word equations and embedded images during in-branch conversion
- Configurable upload limits, session lifetime, credentials, and data locations
- Automated integration tests with `pytest`

## How Access Works

1. Open the dashboard and submit an email address.
2. An administrator signs in to `/admin/login` and approves the request.
3. The approved user can access the tools from the dashboard.
4. Administrators can revoke access from `/admin/approvals`.

Join requests are stored in a JSON file under the Flask instance directory by default. Uploaded documents are processed by the relevant tool and are not kept as a permanent upload library.

## Requirements

- Python 3.10 or newer
- Node.js and npm for the bundled Unicode-to-Bijoy converter
- A modern web browser

## Local Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the application:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Configuration

The application reads configuration from environment variables. Set production values before deployment, especially `SECRET_KEY` and `ADMIN_PASSWORD`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `HOST` | Server bind address | `127.0.0.1` |
| `PORT` | Server port | `5000` |
| `FLASK_DEBUG` | Enable Flask debug mode | `0` |
| `SECRET_KEY` | Flask session signing key | Development fallback |
| `ADMIN_USERNAME` | Administrator username | `admin` |
| `ADMIN_PASSWORD` | Administrator password | Development fallback |
| `SESSION_DAYS` | Session lifetime in days | `365` |
| `MAX_UPLOAD_BYTES` | Maximum upload size | `26214400` (25 MB) |
| `JOIN_REQUESTS_FILE` | Join-request JSON file path | `instance/join_requests.json` |
| `LANGUAGETOOL_URL` | LanguageTool API endpoint | Public LanguageTool API |
| `SPELLCHECK_ENABLED` | Enable spell checking | `true` |
| `BN_WORDLIST_PATH` | Custom Bangla wordlist path | Bundled wordlist |

Example PowerShell configuration:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
$env:PORT = "5000"
python app.py
```

Do not commit secrets or production join-request data to Git. Keep the `instance/` directory private and back it up according to your deployment requirements.

## Routes

| Route | Description |
| --- | --- |
| `/` | Main dashboard and access request form |
| `/tools/bangla-convert` | Unicode/Bijoy converter |
| `/tools/model-test-generate` | Model test DOCX generator |
| `/tools/question-proofreader` | MCQ parser, duplicate checker, and spell checker |
| `/tools/table-converter` | Table-based DOCX converter |
| `/tools/in-branch-question-convert` | Unicode/Avro to SutonnyMJ converter |
| `/admin/login` | Administrator login |
| `/admin/approvals` | Manage join requests |

## Testing

Run the root integration test suite from the project directory:

```powershell
python -m pytest -q
```

The tests cover dashboard and access-control behavior, DOCX conversion downloads, MCQ parsing, and preservation of equations and images.

## Project Structure

```text
.
|-- app.py                         # Flask application entry point
|-- requirements.txt               # Root Python dependencies
|-- master_dashboard/              # Dashboard, routes, access control, and services
|   |-- templates/                 # Shared dashboard and tool templates
|   |-- static/                    # Shared CSS and JavaScript
|   `-- converters/                # Node-based conversion helpers
|-- modules/                       # Integrated standalone tools and source assets
|-- instance/                      # Runtime join-request data
`-- tests/                         # Root integration tests
```

## Deployment Notes

`app.py` is suitable for local use and simple deployments. For production, run Flask behind a production WSGI server or a reverse proxy, configure a strong secret and administrator password, restrict access to the admin routes, and use persistent storage for `JOIN_REQUESTS_FILE`.

## License

No license has been added yet. Add a license file before distributing this project publicly.
