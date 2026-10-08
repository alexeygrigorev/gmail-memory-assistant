# Demo: Gmail replies that learn from corrections

Start the backend and install the extension using [README.md](README.md).
Use test messages sent between accounts you control: one speaker invitation,
another online guest-session invitation, and a sponsorship inquiry. The demo
happens in real Gmail. Generated replies can stay as drafts.

Saved preferences survive refreshes and server restarts. For a clean run,
follow the reset instructions in README.md. Memory is always
enabled, so inspect the Memory indicator when using existing preferences.

## 1. Draft the first invitation reply

Open **Speaking at the Berlin Data Forum** from Maya and click Gmail's **Reply**.
Click **✦ Draft reply** above the message body. Review the reply and expand
the top-right **Memory** indicator. **Memory · 0** means no preferences were used.
The first reply may already ask sensible questions; the demonstration does not
depend on it being bad.

## 2. Teach a reusable preference

Click **Refine** and enter:

> For speaker invitations, keep replies under 100 words. Before accepting,
> ask about the audience, the session length, and the exact date. Use a warm,
> direct tone. For online sessions, also ask whether the recording will be
> publicly available. Do not offer live coding.

Click **✦ Draft again**. The revised reply replaces the text in Gmail's editor.
Expand the preference count to inspect the rules the agent reports applying.
The agent may combine rules or save several memories; show the actual result.

## 3. Open a different invitation

Open **Guest session for ML Builders** from Daniel, click **Reply**, and click
**✦ Draft reply** without repeating the correction. Each Gmail thread has its
own conversation history, while saved preferences are shared.

Review whether the reply asks about the audience, length, date, and recording
policy, and avoids offering live coding. Expand the preference count to inspect
the reported use. Exact wording varies between runs.

## 4. Check relevance

Open **A possible partnership with DataTalks.Club** from Priya and draft a reply.
Speaker-specific preferences should not apply to this sponsorship inquiry.
With only speaker memories stored, the indicator should show **Memory · 0**. General
or previously saved sponsorship preferences can still apply.

The result to demonstrate: one correction reduces repeated edits on the next
relevant email, without applying those rules to unrelated correspondence.
