# Psyche

> **Archived project.** Psyche is a collection of prototypes exploring fraud and deception detection. It is no longer maintained, and I have not recently verified the applications or dependency stacks on a current environment.

**Approaches to detecting fraud enabled or amplified by AI.**

Psyche grew from a broader question: as AI makes it easier to automate online activity, reproduce convincing websites, clone voices, and conduct persuasive conversations at scale, what signals could applications use to recognize suspicious interactions while they are happening?

The repository explores three different parts of that problem: distinguishing automated browsers from human-operated ones, detecting websites that impersonate trusted organizations, and analyzing conversations for signs of scams or social engineering.

## Browser fingerprinting

`browser_fp/` explores whether browser-level signals can help distinguish a genuine browser session from an automated or instrumented environment.

The motivation was the expectation that more online activity would eventually be carried out by AI agents and browser automation. In some applications, it could become important to know whether a request came from a person using a normal browser or from software controlling or emulating one.

The service collects browser attributes and signals associated with automation, including WebDriver, headless-browser characteristics, and inconsistencies in the browser environment. It also generates a fingerprint that can be used to recognize a browser across requests.

`demo/` shows one possible use of those signals in a login flow. A login attempt from a normal browser can proceed when the fingerprint service classifies the browser as genuine, while an attempt made through an instrumented browser such as Playwright can be blocked.

The prototype was intended to explore whether browser characteristics could provide evidence that an interaction was being performed by automation rather than a human-operated browser. It is not a complete bot-detection or account-security system.

## Phishing detection

`phishing/` explores approaches to detecting websites that impersonate legitimate organizations.

One motivation was that generative AI could make it much cheaper to create convincing copies of existing websites. If visual quality, writing quality, and page structure become easy to reproduce, traditional clues such as spelling mistakes or poorly copied layouts become less useful.

The approach here is to determine **what organization a page appears to represent**, then compare that identity with the domain actually hosting the page.

The main workflow:

1. accepts a URL
2. captures a screenshot of the page
3. extracts visible text using OCR
4. asks an LLM to identify the apparent organization or brand
5. determines the expected website for that organization
6. compares the expected domain with the domain of the submitted URL

A mismatch between the apparent brand and the actual domain becomes a phishing signal.

For example, a page might visually present itself as a bank while being hosted on a domain unrelated to that bank.

The repository also contains several approaches to extracting brand identity visually. These include locating likely logo regions using image position and shape, applying OCR, and trying external vision models for logo and web-entity detection.

Not all of these approaches are connected to the primary scanning workflow. They represent different ways I was exploring the problem of determining what identity a webpage was attempting to present.

## Social engineering detection

`social_engineering/` explores whether the content and progression of a conversation can reveal signs of a scam or social-engineering attempt.

The motivation was that AI-generated speech and voice cloning could make it increasingly difficult to rely on a caller's voice or apparent identity alone. A convincing caller could instead be detected through what they are asking for, how the conversation develops, and whether they are attempting to manipulate someone into taking an unsafe action.

The prototype processes recorded audio in short chunks, transcribes the speech, attempts to associate speech with individual speakers, and asks an LLM to assess whether the conversation contains signs of scams or social engineering.

The interface presents:

- the evolving transcript
- speaker labels
- a risk assessment
- the reasoning behind that assessment

The emphasis was on analyzing the **conversation itself** rather than attempting to determine whether a voice was synthetically generated.

The implementation uses uploaded or recorded audio and file-based chunk processing. It is not connected to a live telephone system, and it does not perform cloned-voice detection.

## Repository structure

```text
browser_fp/          Browser fingerprinting and automation detection
demo/                Login flow using the fingerprint decision
phishing/            Website capture and phishing analysis
social_engineering/  Audio and conversation analysis
creepjs/             Modified CreepJS used by the fingerprinting prototype
```

These are separate prototypes rather than components of a single finished fraud-detection service.

## Third-party code

`creepjs/` contains a modified copy of [CreepJS](https://github.com/abrahamjuliot/creepjs), used by the browser-fingerprinting prototype.

Its original MIT license is retained in [`creepjs/LICENSE`](creepjs/LICENSE). The repository's root license applies to the original Psyche code.

