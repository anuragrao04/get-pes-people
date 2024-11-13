# GetPESPeople

## What It Does?

It Gets SRNs, PRNs, Classroom Info, Campus Info, Semester, Section of everybody at PES University, Both EC and RR campus, in under 5 minutes.

## How It Works?

It sends requests to the backend of PESU Academy and exploits the 'know your class and section' feature. It parses the returned table and stores it all in an sqlite database for you to integrate into other applications. 

## How To Run It? 

1. Populate `.env.example`. To do this, go to [pesuacademy](https://pesuacademy.com), open your `networks` tab in your browser's dev tools, then login. After logging in, take the most recent request in the networks tab and inspect the most recent request headers. You will see your cookie and CSRF token. Copy these and put it into `.env.example` in the format mentioned
2. Rename `.env.example` to `.env`
3. Make a python virtual environment if needed: `python3 -m venv .venv`
4. Install the requirements/dependencies: `python3 -m pip install -r requirements.txt`
5. Run `main.py` as `python3 main.py <current year>` where current year is the year is the **year of admission of the most youngest batch**. As of writing, this is 2024. For example: `python3 main.py 2024`
6. Sit back and enjoy

## Contributing

Contributions are welcome. Please create an issue before working on something you want merged later.
