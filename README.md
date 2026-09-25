# Psyche

> **Archived project.** Psyche is a collection of older experiments in fraud and deception detection. It is no longer maintained, and I have not recently verified the full applications or dependency stacks on a current environment.

**Experiments in detecting fraud from browser, web, and conversation signals.**

Psyche grew from a question: can an application recognize a suspicious interaction from the signals available while it is happening? A browser, a website, and a conversation each reveal different clues. These prototypes explore what those clues might tell us.

## Browser fingerprinting

`browser_fp/` explores whether browser characteristics can help distinguish a human-operated browser from automation or an emulated environment. The concern was that, as AI agents and browser automation became more common, applications might need a way to assess *how* someone was interacting with them, not just whether a device had visited before.

The prototype collects browser attributes and signals associated with automation, including WebDriver, headless mode, and inconsistencies in the browser environment. It stores a fingerprint so it can recognize a returning browser and use its history when evaluating a request.

`demo/` is a small login example. The sign-in page collects a browser fingerprint and sends its ID along with the login attempt. The fingerprint service can return `Accept`, `Review`, or `Blocked`. The demo admits an `Accept` result if the credentials also authenticate, then shows a welcome page with the user's email. Other results appear as a bot warning on the login form. It illustrates a possible use of the fingerprint decision; it is not a complete account-security flow.

## Phishing detection

`phishing/` explores a different problem. AI could make it cheap to produce convincing copies of real websites at scale. If a fake site looks almost identical to the original, clues such as poor spelling or a roughly copied layout become less useful. The question was whether a scanner could work out *which organization a page claims to represent*, then compare that claim with the address where the page is hosted.

The web prototype takes a URL and queues a scan. It captures a screenshot, reads visible text with OCR, and asks an LLM to identify the apparent brand and its expected website. It then compares the registered domain of that expected website with the submitted URL. A mismatch is a phishing signal. The interface displays the scan result and the information used to reach it.

There are also experiments in finding a site's logo automatically. They look for likely logo regions near the top of a screenshot using position, shape, and image-processing clues, then try OCR. Separate scripts explore Google Vision logo and web detection and GPT-4 Vision. These experiments show where visual brand recognition might have taken the scanner; they are not all part of the queued web scan. The screenshot tool saves page HTML, but the current scan does not use page metadata in its verdict.

## Social engineering detection

`social_engineering/` was motivated by another possible effect of AI: convincing voice cloning could make a scam call harder for a person to recognize. A caller might gradually pressure a support worker into bypassing a policy, such as resetting an account and disclosing access details. I wanted to explore whether the *conversation itself* could reveal that kind of manipulation as it developed.

The prototype accepts recorded audio, processes it in short chunks, transcribes speech, attempts to label speakers, and asks an LLM whether the conversation suggests a scam or social engineering. Its interface shows the transcript, speaker labels, a risk indication, and the model's reasoning.

This is an early exploration of conversation analysis using the speech and language models available at the time. The implemented prompts ask about scams and social engineering in general; they do not check a specific support-center policy or detect a cloned voice. Audio is uploaded or recorded and processed in chunks, rather than connected to a live phone system or classified after every conversational turn.

## Repository structure

```text
browser_fp/          Browser fingerprinting service
demo/                Login example using a fingerprint decision
phishing/            Website capture and phishing analysis
social_engineering/  Audio and conversation analysis
creepjs/             Modified CreepJS used by the fingerprinting prototype
```

These are separate prototypes, not components of a single finished fraud-detection service.

## History

This repository was extracted from the original FraudIQ work. The retained files keep their original Git authors and commit dates. The extraction changed commit IDs because unrelated code and committed credentials were removed from the new history. The directory names and this README were added afterward.

## Third-party code

`creepjs/` contains a modified copy of [CreepJS](https://github.com/abrahamjuliot/creepjs). Its MIT license is retained in `creepjs/LICENSE`. The repository's root license applies to the original Psyche code.

## Note

This project is archived. Its applications and dependencies have not been revalidated on a current environment. The login demo also still points to an older fingerprint-service URL and would need that path updated before it could be run with the renamed `browser_fp/` service.
