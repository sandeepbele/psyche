# Psyche

Experiments in recognizing fraud from three kinds of evidence: the browser visiting an application, the website a person is asked to trust, and the conversation taking place on a call.

The projects grew out of a question: can an application identify a suspicious interaction while it is happening, using the signals already available at that point? A browser can reveal signs of automation or a returning device. A website can claim to be a familiar brand while living on a different domain. A call can sound routine until a request or pattern of persuasion changes its meaning.

| Area | What the prototype does |
| --- | --- |
| `browser_fp/` | Collects browser fingerprint signals, recognizes returning devices, looks for bot behavior, and uses those signals in a login demo. |
| `phishing/` | Captures a webpage, extracts its text with OCR, asks an LLM what the page appears to represent, and compares the claimed brand with the URL. |
| `social_engineering/` | Transcribes chunks of a recorded conversation, associates speech with speakers, and asks an LLM to assess possible scam or social engineering behavior. |

These are historical prototypes, not a single production service. The call analysis uses uploaded audio and file-based streaming; it does not connect to a phone system. The phishing workflow includes a web UI and queued scanning tasks. The browser work includes a separate Django service and login demo.

## History

This repository was extracted from the original FraudIQ work. The retained files keep their original Git authors and commit dates. The extraction changed commit IDs because unrelated code and committed credentials were removed from the new history. The directory names and this README were added afterward.

## Third-party code

`creepjs/` contains a modified copy of [CreepJS](https://github.com/abrahamjuliot/creepjs), used by the browser fingerprint prototype. Its original MIT license is kept in [`creepjs/LICENSE`](creepjs/LICENSE). The repository's root license covers the original Psyche code.

## Note

This is an archived showcase of the ideas and code as they developed. The dependency versions and full application flows have not been verified against a current environment.
