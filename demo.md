# Demo scenario: an email assistant that learns from corrections

## The story

Alexey receives invitations to speak at events. An AI assistant can draft a
reply, but Alexey usually edits it to ask for missing details before accepting.

In this demo, Alexey teaches those preferences while replying to one
invitation. The assistant saves the corrections in Actian VectorAI DB.
When a different invitation arrives, it retrieves the relevant preferences
and applies them in a fresh conversation.

The practical benefit is fewer repeated edits on the next email.

## Before presenting

Start the app using the instructions in [README.md](README.md), then open
[localhost:8000](http://localhost:8000).

The inbox contains fictional messages. The app generates editable replies;
it does not send email. Allow about five minutes for this walkthrough.

Previously saved preferences survive browser refreshes and server restarts.
Check the memory panel before describing a run as having no prior preferences.
For a baseline without saved preferences, turn off **Use learned preferences**
and generate a draft. Turning it back on clears the displayed draft and starts
a fresh conversation for that email.

## 1. Draft a reply to the first invitation

Open Maya Chen's **Speaking at the Berlin Data Forum** email. Leave
**Use learned preferences** on and click **Draft reply**.

Explain:

> Maya wants me to speak at an event. The assistant can write a reasonable
> reply, but I have a particular way of handling invitations. I want to teach
> that once rather than repeat it for every organizer.

Show the editable reply and **Memories used for this draft**. With no saved
preferences, this section reports zero preferences. If preferences already
exist, it shows the ones the assistant reports applying.

Do not rely on the first draft being bad. It might already ask sensible
questions about the event.

## 2. Teach a reusable preference

Paste this into **Tell the assistant what to change**:

> For speaker invitations, keep replies under 100 words. Before accepting,
> ask about the audience, the session length, and the exact date. Use a warm,
> direct tone. For online sessions, also ask whether the recording will be
> publicly available. Do not offer live coding.

Click **Revise**.

The correction includes a distinctive preference about recordings and live
coding, so the next reply has something specific to carry forward. The
**Try a correction** button supplies the shorter version without those two
extra preferences.

Show:

1. The revised reply.
2. The saved preference or preferences in **Drafting memory**.
3. The preferences reported as used for the revised draft.

Explain:

> This correction applies to future speaker invitations. The assistant
> stores it as a preference, rather than keeping it only in this conversation.

The assistant may combine related instructions into one memory or save
several memories. Show the actual saved content rather than promising a
particular number of records.

## 3. Open a different invitation

Open Daniel Rivera's **Guest session for ML Builders** email and click
**Draft reply**. Do not repeat the correction.

Selecting this email starts a fresh conversation. Daniel is inviting Alexey
to an online session, so the recording preference now applies.

Explain:

> This is a different sender and a new conversation. The earlier conversation
> history is gone. The assistant retrieves the preferences relevant to this
> invitation from VectorAI DB.

Review the reply. It should stay concise, ask for the audience, session
length, date, and recording policy, and avoid offering live coding.

An illustrative reply is:

```text
Subject: Re: Guest session for ML Builders

Hi Daniel,

Thanks for the invitation and the kind words. I'd be interested in learning
more before confirming.

Could you share the audience's experience level, the session length, and
the exact date in December? Will the recording be publicly available?

Once I have those details, I can check whether this would work for me.

Best,
Alexey
```

The model's wording will vary. This example is a target behavior, not a
fixed response.

Expand **Memories used for this draft** and point to the learned preference.
The UI labels this as the assistant's report of what it applied. The
separate **Drafting memory** panel shows retrieval candidates and saves;
retrieving a memory alone does not mean the assistant used it.

## 4. Compare with memory off

While viewing Daniel's email, turn off **Use learned preferences** and click
**Draft reply** again.

Show that the usage section says **Memory off**. The saved preferences are
neither retrieved nor updated in this mode.

Compare the two drafts, particularly the recording question and the offer
of live coding. A model without memory may independently ask some of the
same questions. The evidence of continuity is the saved correction and
its reported use in the new conversation, alongside the reply itself.

## 5. Check that preferences stay relevant

Turn memory back on. Open Priya Shah's **A possible partnership with
DataTalks.Club** email and click **Draft reply**.

The reply should address the sponsorship inquiry. It should not ask about
session length or recording policy merely because those preferences were
saved for speaker invitations.

Show the memories reported as used. If the only stored preferences are
speaker-specific, the expected selection is empty. General preferences or
previously saved sponsorship preferences may still apply.

Explain:

> Remembering everything is not enough. The assistant needs to select the
> preferences that fit the current email.

## Closing line

> I corrected one reply, and the next relevant email needed fewer edits.
> VectorAI DB gives the assistant persistent, searchable memory of those
> corrections across conversations.
