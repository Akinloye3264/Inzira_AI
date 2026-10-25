# Inzira Lite Model Card

## Purpose

Inzira Lite is an accessible first-stage household economic-vulnerability
screening tool for Rwanda. It uses approximately 12 user-facing questions and
19 model predictors.

It complements the detailed Inzira professional model. It is not an official
poverty classification system.

## Intended users

- Households performing an initial self-assessment
- Field officers conducting an assisted assessment
- Community organisations identifying households for further review
- Competition judges evaluating the Inzira AI prototype

## Model

- Algorithm: Compact XGBoost
- Target: Vulnerable versus non-poor
- Decision threshold: 0.49
- User-facing questions: 12
- Processed model predictors: 49
- Supported interface languages: Kinyarwanda and English
- Default interface language: Kinyarwanda

## Final locked-test results

- Accuracy: 0.7734
- Balanced accuracy: 0.6783
- Macro F1: 0.6815
- Vulnerable precision: 0.5246
- Vulnerable recall: 0.4972
- Vulnerable F1: 0.5105
- ROC AUC: 0.7933
- Average precision: 0.5466
- Brier score: 0.1502

Bootstrap 95% confidence intervals:

- Macro F1: 0.6607–0.7041
- ROC AUC: 0.7730–0.8134

## Missing-answer robustness

Test macro F1:

- Complete answers: 0.6815
- 10% unanswered: 0.6972
- 20% unanswered: 0.6941
- 30% unanswered: 0.6926

These simulated results do not imply that missing information improves
prediction. They show that the preprocessing pipeline remains operational when
some question groups are unanswered.

## Fairness limitations

The final audit identified:

- Province recall gap: 0.1943
- Urban–rural recall gap: 0.0367
- Sex-of-household-head recall gap: 0.0743
- Household-size recall gap: 0.4974

Recall for vulnerable households containing one to three members was 0.2014.
The interface must therefore recommend a complete assessment for small
households even when the Lite screening score is below its threshold.

## Required safeguards

- Never display the label “not vulnerable.”
- Never deny assistance using the screening result.
- Always provide a route to professional assessment.
- Show data completeness with every result.
- Show the small-household limitation notice when applicable.
- Do not describe province as causing vulnerability.
- Require human review for material decisions.

## Translation status

The Kinyarwanda interface content is a structured draft. It requires review
and approval by a fluent Kinyarwanda speaker before public deployment.

## Prohibited uses

Inzira Lite must not be used alone to:

- approve or deny social assistance;
- approve or deny credit or insurance;
- remove an existing benefit;
- produce an official poverty classification;
- rank households without an appeals or human-review process.

## Data policy

The deployment bundle contains no raw EICV7 microdata, names, telephone
numbers, national identification numbers or household-level test predictions.

## Development status

The model, threshold and test evaluation are final. Test results must not be
used for further model tuning.
