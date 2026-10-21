# Usability evaluation

## Purpose

The proposal target is at least 14 of 15 tasks completed without help across five users. A real five-owner study was not available during software construction. To avoid inventing participant data, this pack records a preliminary scripted walkthrough and gives the exact protocol for the group's field session.

## Preliminary scripted walkthrough

Five device and data scenarios were used: narrow phone, large phone, tablet, laptop, and keyboard-only laptop. Each scenario completed three core tasks, giving 15 task attempts.

| Scenario | Record sale | Prepare draft basket | Approve and receive | Result |
|---|---|---|---|---|
| Narrow phone (360 px) | Pass | Pass | Pass | 3/3 |
| Large phone (430 px) | Pass | Pass | Pass | 3/3 |
| Tablet (768 px) | Pass | Pass | Pass | 3/3 |
| Laptop (1440 px) | Pass | Pass | Pass | 3/3 |
| Keyboard-only laptop | Pass | Pass | Pass | 3/3 |

Scripted result: **15/15 tasks completed**. This result supports interface readiness but is not a substitute for five independent users.

## Issues found and changes made

| Observation | Risk | Change |
|---|---|---|
| A long stock table is difficult on a phone | Owner may lose the product name | Horizontal table scrolling and a search box were added |
| Users need clear calculation feedback | A slow request may look broken | Loading skeleton, error panel and retry button were added |
| Order status was easy to miss | A delivery could be received twice | Colour-coded status badges and status-dependent buttons were added |
| Invalid sales could create impossible records | Stock balance could become negative | API rejects the movement and gives the available quantity |
| Navigation could take too much mobile width | Main tasks may be hidden | Collapsible mobile menu was added |

## Field-session protocol

Recruit five adult volunteers, preferably spaza owners or people familiar with small retail. Obtain voluntary consent and do not record customer information. Give each person the same short introduction and test account.

Ask each person to:

1. record a sale of two units;
2. find a low-stock product;
3. calculate a basket for one supplier;
4. explain why a quantity is a full pack;
5. create the draft order;
6. approve the draft; and
7. receive the order.

For the proposal's 15-task measure, score the first three tasks for each user as pass without help, pass with help, or fail. Record time, errors and comments for all seven tasks.

## Result sheet for five real participants

| User code | Task 1 without help | Task 2 without help | Task 3 without help | Time | Errors/comments |
|---|---|---|---|---|---|
| U01 |  |  |  |  |  |
| U02 |  |  |  |  |  |
| U03 |  |  |  |  |  |
| U04 |  |  |  |  |  |
| U05 |  |  |  |  |  |

Do not replace blank fields with invented results. Update the final report after the real session and list any usability changes made.

