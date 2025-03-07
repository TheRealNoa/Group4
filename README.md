Building a classification model using patient data to classify patients as either newly
diagnosed or relapsed into one of the following classes (Lung, Prostate, CLL,
Colorectal, and Breast cancers). The model should classify the patients and
recommend open cancer clinical trials in Ireland based on the cancer subtype.
Data sources for creating patient profiles based on newly diagnosed or relapsed
patients can be created using historical clinical trials for these disease groups.
Data sources: https://www.cancertrials.ie/ (for identifying open clinical trials in ireland
and creating patient profiles)

---------------------------------------------------------------------------------------------------
**Project tasks distribution:**
Establishing a connection between our app, cancertrials.ie and clinicaltrials.gov
-Keep track of active trials, categorize cancer types- look at patient profile info provided on the website
-Find a way to link the clinicaltrials.ie link to clinicaltrials.gov. So: Expect the model to be able to find the "participation criteria" in one smooth pipeline. -Noa

-List the requirements: Inclusion and Exclusion parameters for each cancer type (just one rn but keep in mind) -Muadh

Profile of trials: (for laterzzz)
Being able to take the requested participation criteria and create a sort of "criteria" with an LLM so that we can later compare it to a patient profile.- Eryk

Fake patients dataset:
For each cancer (breast cancer only for now) type, take as much info as possible from the available trials in order to then create a small dataset of non-existing patients.- Shauna

Patient profiles (LLM):
Taking data from the patients dataset, feeding it into the LLM, classifying relapsed or newly diagnosed, fitting the data so we can compare it to the trials "criteria"- Aron


Matching patient to profile (LLM):
Taking the two inputs:
One of applicable trials criteria, one of patient profiles and finding if there exists a trial that can be matched to the patient.- Marcus
