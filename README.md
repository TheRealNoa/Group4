# How it works
###### login:
You need to go to the patients.csv file and use a patient's ID with the @hse.ie domain to login.
It can be any user ID and for the password, you can input anything.

###### user interface:
You can sellect/edit the following:
* Country
* Cancer Type
* Patient Name
* Patient age
* Diagnosis type

You can also update this data in patients.csv by clicking the "Update patient details" button

###### trial scraping:
Once the user gives a full input, based on the country and cancer type, we look for currently open clinical trials. The user is then prompted with all the results, ordered by least exclusion criteria -> most exclusion criteria.
Each result gives you the options to:
* Show/hide eligibility criteria
* Click on the title of the trial to bring you to the clinicaltrials.org page for that trial
## To setup
###### For Windows:
open cmd in the project directory
venv\\Scripts\\activate
python app.py
visit  http://localhost:5000 in your browser

If for some reason that doesn't work, try:
open cmd in the project directory
python -m venv venv
venv\\Scripts\\activate
pip install flask beautifulsoup4 requests
python app.py
visit  http://localhost:5000 in your browser

###### For Linux:
open cmd in the project directory
remove venv if it exists
python3 -m venv venv
source venv/bin/activate
pip install flask beautifulsoup4 requests
python app.py
visit  http://localhost:5000 in your browser

###### For Mac:
open Terminal in the project directory

create a new virtual environment:
python3 -m venv venv

activate the virtual environment:
source venv/bin/activate

install dependencies:
pip install flask beautifulsoup4 requests

run the app:
python app.py

visit  http://localhost:5000 in your browser
