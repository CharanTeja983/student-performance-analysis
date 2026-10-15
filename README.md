# Student Performance Analysis System

A beginner-friendly Flask + MySQL web app for managing student records and marks, analysing academic performance with Pandas/NumPy, and displaying Matplotlib charts.

## Features
- Register, edit, list, and delete students
- Add/update/delete subject marks (Mathematics, Science, English by default)
- Dashboard totals, overall average, pass percentage, toppers, and students needing support
- Subject-wise averages and student-level performance table
- Matplotlib charts and CSV export
- MySQL health-check endpoint at `/health`

**Pass rule:** this starter project treats a subject result of 35% or more as a pass. Change the threshold in `app.py` if your institution uses a different rule.

## 1. Prerequisites
- Python 3.10 or newer
- MySQL Server (and optionally MySQL Workbench)
- Git
- A terminal / VS Code

## 2. Create the MySQL database
Start MySQL Server. In MySQL Workbench, open `schema.sql` and execute it, or run:

```sql
CREATE DATABASE student_performance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The application creates its tables automatically on startup.

## 3. Configure the application
Open a terminal in this project folder:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**
```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

If Windows says Python was not found, install Python from https://www.python.org/downloads/, enable **Add Python to PATH**, then reopen the terminal. You can also try `py -m venv .venv`.

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and edit `DB_USER`, `DB_PASSWORD`, and other values for your local MySQL server.

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**Windows Command Prompt**
```bat
copy .env.example .env
```

Never commit `.env` or real passwords to Git.

## 4. Run the app
With MySQL running and the virtual environment activated:

```bash
python app.py
```

Open the local URL shown in the terminal, usually http://127.0.0.1:5000.

Recommended workflow:
1. Open **Students** and register a few students.
2. Open **Marks** and add each student's subject marks.
3. Open **Dashboard** and **Analysis** to view the summaries and charts.
4. Use **Export CSV** on the Analysis page to download the analysis data.

`http://127.0.0.1:5000/health` reports whether the app can connect to MySQL.

## 5. Push the project to GitHub
Create a new **empty** repository on GitHub (do not add a README or `.gitignore` there if you already have these locally). Then run from the project folder:

```bash
git init
git add .
git status
git commit -m "Initial commit: Student Performance Analysis System"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/student-performance-analysis.git
git push -u origin main
```

Replace `YOUR-USERNAME` and the repository name with your actual GitHub details. GitHub may ask you to authenticate in a browser or with Git Credential Manager. Do not put your password or token in the remote URL.

If a remote already exists:
```bash
git remote -v
git remote set-url origin https://github.com/YOUR-USERNAME/student-performance-analysis.git
```

If Git says `remote origin already exists`, use `git remote set-url` instead of `git remote add`.

## 6. Common issues
- **Can't connect to MySQL:** confirm the MySQL service is running and check `.env`.
- **Access denied:** verify MySQL username/password and privileges.
- **Unknown database:** run the `CREATE DATABASE` statement or execute `schema.sql`.
- **`python` not recognized:** install Python with PATH enabled, reopen terminal, or use `py`.
- **Port 5000 is busy:** stop the other app or change the port in `app.run(...)`.
- **Changes are not pushed:** run `git status`, then `git add .`, `git commit`, and `git push`.

## Notes
This is an educational starter project, not a production-ready deployment. Before production use, add authentication/authorization, CSRF protection, migrations, stricter input validation, and secure production configuration. Do not expose the Flask debug server publicly.
