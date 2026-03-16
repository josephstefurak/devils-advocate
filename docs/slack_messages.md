This is the very beginning of your direct message history with @Deji Olaleye, @Joseph Stefurak, and @Zaina Qasim
You’ll be notified for every new message in this conversation. Change this setting
Deji Olaleye
  6:55 PM
GIF
https://media.tenor.com/qeSrYLUCe0kAAAAM/power-rangers.gif

Sean Kraemer
  6:57 PM
Hi everyone, looking forward to working with you all on the group project!
Zaina Qasim
  8:17 PM
Likewise!
Joseph Stefurak
  2:32 PM
Hey guys just to keep everyone in the loop I had claude create a summary of what Zaina and I were brainstorming. Dont put too much weight into the specifics, all the details are tbd.
PDF


devils_advocate_summary.md.pdf
PDF
2:33
Goes without saying but super interested in hearing what you guys think and if you have any ideas/input
Joseph Stefurak
  2:34 PM
Also, would you guys be available to meet over zoom this weekend and get the ball rolling?
Deji Olaleye
  3:13 PM
I'm a fan of that idea, love the concept of a conversational agent meant to challenge the user
Sean Kraemer
  3:14 PM
Thanks for sharing the project idea @Joseph Stefurak, it looks pretty interesting to me. I'm free to discuss almost anytime this weekend except saturday evening.
Zaina Qasim
  3:14 PM
Fyi here's the Excalidraw from our brainstorming session: https://app.excalidraw.com/s/1V0DgO95JSK/8RGMM4pxOzs
Excalidraw+
Whiteboarding made easy
Whiteboarding tool with hand drawn like experience. Ideal for conducting interviews, drawing diagrams, prototypes or sketches and much more!
https://app.excalidraw.com/s/1V0DgO95JSK/8RGMM4pxOzs

Zaina Qasim
  3:17 PM
replied to a thread:
Also, would you guys be available to meet over zoom this weekend and get the ball rolling?
How about 10-11 am on Sunday? @Joseph Stefurak does that work for you?
Joseph Stefurak
  7:23 PM
Could we do 11 am - noon on sunday?
Joseph Stefurak
  7:23 PM
If that works for everyone I can set up the zoom
Sean Kraemer
  8:52 AM
yeah that time works for me!
Joseph Stefurak
  12:36 PM
https://illinois.zoom.us/j/87880771325?pwd=iErUS48a9HORjpVVOQnb80VtYrDQKC.1
Sean Kraemer
  11:00 AM
are we still good to meet right now?
Zaina Qasim
  11:07 AM
I'm waiting too. @Joseph Stefurak is the host...
11:07
Let me text him
Sean Kraemer
  11:07 AM
https://illinois.zoom.us/j/2116531435?pwd=JM4sPFmXVbLfPknRgvvk9wGEuP7uTg.1
11:07
here just use my link for now
Zaina Qasim
  11:07 AM
Okay (edited)
Zaina Qasim
  11:17 AM
https://gemini3.devpost.com/
gemini3.devpost.com
Gemini 3 Hackathon
Build what's next
Sean Kraemer
  11:33 AM
https://docs.google.com/document/d/1B1MEbRdM1NFQm4iBxVF-HHqLYYRIbditEY_Iwr5yel0/edit?usp=sharing
Zaina Qasim
  12:18 PM
@Deji Olaleye could you share the Goolge doc again?
Deji Olaleye
  12:20 PM
Sure, one sec
12:21
https://docs.google.com/document/d/1hSUlMx05CBxLFIFVJtYSieURVpBXCwJAn96NLedRpPg/edit?usp=sharing
Zaina Qasim
  12:21 PM
Thank you!
Sean Kraemer
  12:25 PM
set the conversation topic: CS 568 Final Project Group
Zaina Qasim
  2:23 PM
@here Hey guys, I put a very rough draft together for the abstract in Abstract tab based on our discussion from today. I've added comments for what needs to be filled in. @Sean Kraemer Let me know if this is helpful/anything I can clarify regarding what I wrote. I hope this reduces your workload a bit and lets you focus more on the literature review (main gap imo).  We do need to define the evaluation methodology a little better as well @Deji Olaleye would you be able to own this piece?
I'll work on the architectural diagram and add it to our proposal by EOD or Monday morning at the latest.
Sean Kraemer
  3:58 PM
Thanks for getting the draft done @Zaina Qasim!! I'll take a look and try to proofread/revise. Also, I'll look into the lit review for the evaluation of our agent system. (edited)
Joseph Stefurak
  4:18 PM
Here a quick summary of what I’ve done so far:
Here’s a breakdown of how I see the 5 “chunks” of what it’ll take to fully build out the tool:
Chunk 1: Core MVP - getting the live debate working
Chunk 2: Make it smart - add grounding, knowledge base, Google search, better prompting. Also add document input and ingestion.
Chunk 3: Multi-agents: Here we can add a judge and some summary/evaluation.
Chunk 4: Research Data Pipeline: collect data/implementations specifically for the study.
Chunk 5: Deploy + Polish + Test + Documentation
What I did today:
Chunk 1:
This is the MVP. Everything else builds on top of it.
Set up a Google Cloud project, enable Gemini Live API
Built a minimal React frontend with microphone input
Opened a bidirectional WebSocket to Gemini Live — confirmed you can talk and hear a response
Wrote the devil's advocate system prompt — lock it into a position, prevent it from going helpful-assistant mode. This needs to be tweaked a lot but works for now
Added basic session state so the agent remembers its committed position across turns.
Everything is being ran locally except for the Gemini calls.
No readme yet either because there’s gonna be big changes so it would get outdated really fast. Gonna start working on Chunk 2 now.
Public repo of chunk1 code: https://github.com/josephstefurak/devils-advocate
GitHub
GitHub - josephstefurak/devils-advocate
Contribute to josephstefurak/devils-advocate development by creating an account on GitHub.
https://github.com/josephstefurak/devils-advocate

4:19
Heres a video demo of the mvp
Chunk1Demo2026-03-01 16-10-28.mov


Generate transcript
Sean Kraemer
  4:24 PM
that's a great starting point, thank you for getting that set up so quick @Joseph Stefurak! Can you add me as a collaborator to the repo? Username: SeanKraemer-UIUC
Joseph Stefurak
  4:25 PM
Yeah invite sent
Sean Kraemer
  4:26 PM
got it and accepted, thanks
Joseph Stefurak
  4:28 PM
The core prompt is super aggressive right now so it doesnt really help you get ideas it mainly just rips you apart
4:28
You are Devil's Advocate — an intellectual adversary in a live spoken debate.
THE USER'S POSITION:
"{user_claim}"
YOUR ROLE:
You have committed to opposing this position for the entire debate. This is non-negotiable.
You will argue AGAINST the user's business idea with sharp, specific, grounded counterarguments.
DEBATE RULES — FOLLOW THESE EXACTLY:
1. Never concede your core position. Ever. You may say "that's an interesting point" but
   immediately pivot to why it doesn't save their argument.
2. Never say "you're right" or "great point" or "I agree." You are an adversary, not a coach.
3. Always be specific. Don't say "your market is risky" — say "your TAM assumes 15% penetration
   in year one which no SaaS company in this category has achieved without $10M+ in sales spend."
4. Escalate. If the user makes a weak rebuttal, push harder. If they make a strong point,
   find a deeper angle — don't capitulate, find the next vulnerability.
5. Focus your attacks on the most dangerous weaknesses: market assumptions, competition,
   unit economics, customer acquisition, and timing.
6. Keep responses concise and punchy — 2-4 sentences max per turn. This is a live debate,
   not a lecture.
7. If the user goes off topic, drag them back to defending their idea.
8. You are not an assistant. Do not offer help, suggestions, or encouragement.
   Your only job is to poke holes.
YOUR COMMITTED POSITION:
This business idea has critical flaws that make it unlikely to succeed. You will prove this
through the debate. You will not change this position regardless of what the user says.
Begin by immediately attacking the weakest assumption in the user's business idea.
Be direct. Be sharp. Start the debate now.
"""
4:32
I loosely followed this to build it. I changed the model though and the code had a lot of bugs/bad features but you get the high level idea
PDF


chunk1_build_guide.md.pdf
PDF
4:33
Also like most of those libraries and tools are depricated
4:33
So in summary dont look at the code but everything else will give you a silhouette
Deji Olaleye
  4:42 PM
Nice, you moved fast @Joseph Stefurak. My github is djolaleye
Joseph Stefurak
  4:44 PM
invite sent
Zaina Qasim
  9:53 PM
Ooo this is great! Could you add me as well? My github account is qasimza
Zaina Qasim
  11:33 AM
@here Hey guys, I am working on the architectural diagram now (my apologies, I had a few intro calls scheduled last minute). I had a few questions for you-
Do you have a preference for server vs serverless architecture?
Do you have a preference for certain web-frameworks/tech-stack/programming languages?
While our hosting/infra will be have to be Google Cloud and our agent will use Gemini Live API (constraints of the hackathon), the rest is upto us. I want to play to our strengths and allow everyone on the team to build skills relevant to their career goals. Let me know your thoughts- I'll incorporate that in the diagram.
Joseph Stefurak
  11:35 AM
Serverless would be ideal but we may need compute instances for the embedding part of rag. I'll look into it. Also for the mvp I used React + Vite (JSX) for the frontend framework and FastAPI + Python for backend. Obv we can change if we want but thats just what I used so far
11:38
PRetty sure we can use Firebase to static host frontend and then we can just containerize the backend and host on Cloud Run (GCP)
11:38
Firebase is nice it should let us do pretty much everything
11:39
After a quick google search doesnt look like wed need a dedicated server for any of it so serverless should work fine
Zaina Qasim
  12:51 PM
I looked into the compute requirements, and you're totally right, we don't need a dedicated server for the RAG embeddings. Cloud Run allows up to 32GB of RAM per container, which is more than enough to hold the embedding models in memory alongside the backend. I am fully on board with the serverless Firebase + Cloud Run architecture! To make sure we move as fast as possible for the hackathon, here is what I am thinking for the stack details. Some of this isn't exactly "architecture" but might as well add this in our proposal:
Backend (Cloud Run)
Framework: FastAPI + Python works for me, although I am open to Node/Express/TS as well (seems to be a popular choice for backend services lately).
Package Manager: Let's use uv for anything Pythonic. It is significantly faster than standard pip and will speed up our container build times immensely.
Frontend (Firebase Hosting)
Framework: React + Vite is great, but I have a strong preference for using TypeScript (TSX) over JavaScript. It makes the codebase much easier to follow and debug when we're moving fast.
Node version: 22 is more stable/faster- we should use that.
Package Manager: Let's use pnpm as our default.
Styling & UI: Let's use Tailwind instead of standard CSS for customization. We should also decide on a UI design kit so we aren't building components from scratch: MUI (Material UI) is a solid popular option if you are cool with that?
Agent Tools/Database:
RagManagedDb seems to be the best for our use case- it's great for document storage, is fully-managed, integrates well with the rest of our setup.
google search for retrieving factual information- market study, current solutions etc.
firestore: Our primary NoSQL database for storing user sessions, debate chat logs, evaluation metrics generated by the judge agent, scores, reports etc. (Happy to use a PostgresSQL db as well since that's what I'm seeing in production lately, but a NoSQL approach might help us move faster.
Auth:
FirebaseUI Auth seems like the way to go for client-side auth.
Firebase Auth SDK for the backend within FastAPI to verify the client-side JWTs.
Tailwind CSS
Tailwind CSS - Rapidly build modern websites without ever leaving your HTML.
Tailwind CSS is a utility-first CSS framework for rapidly building modern websites without ever leaving your HTML.
https://tailwindcss.com/

mui.com
Material UI: React components that implement Material Design
Material UI is an open-source React component library that implements Google's Material Design. It's comprehensive and can be used in production out of the box.
https://mui.com/material-ui/

Zaina Qasim
  6:15 PM
@here Hey guys, I am finally done with the architectural diagrams and some flow diagrams for the different kinds of agents that we need. [Sorry for the delay, its been quite busy today]. Let me know what you think. These don't include all the details [Ex: did not speak to caching, guardrails for judges/report] but I think the more or less communicate the main idea.
4 files


Download all
image.png
image.png
image.png
image.png
Deji Olaleye
  8:50 PM
Looks good, it communicates the process and roles clearly.
Sean Kraemer
  9:09 PM
Those are very clear and well laid out, thank you for getting those done @Zaina Qasim.
Sean Kraemer
  9:16 PM
Also just double checking, the link shared earlier to that gemini hackathon already ended. (https://gemini3.devpost.com/)
was this the hackathon we were looking to participate in? (https://geminiliveagentchallenge.devpost.com/?ref_feature=challenge&ref_medium=discover)

gemini3.devpost.com
Gemini 3 Hackathon
Build what's next

geminiliveagentchallenge.devpost.com
Gemini Live Agent Challenge
Redefining Interaction: From Static Chatbots to Immersive Experiences
Joseph Stefurak
  9:46 PM
Yes that second one
Zaina Qasim
  1:14 AM
Apologies for the mix up - did not realize there were 2. When you guys find a chance could you please join the team on Devpost: https://devpost.com/software/devil-s-advocate-o6z5d1/joins/otUkOwgyq0mW9Oh5_GhTNQ
Sean Kraemer
  10:33 AM
No worries, will join that before EOD. Also sorry for the delay on lit/research review. I ran a gemini deep search on all of our discussions and documents thus far and am going to read through that later today (hopefully before lecture) and add some references+edits to the abstract for us to discuss.
Sean Kraemer
  10:42 AM
also @Joseph Stefurak can you add my other, personal github account to the repo? username is SeanKraemer
I think i might work on the project using my personal instead of my student github
Joseph Stefurak
  4:18 PM
Working through chunk 2 rn should be done soon
4:19
So far ive added live google searching, better transcript streaming
4:19
In the middle of rag and claim tracking
4:19
For rn im just putting in an example knowledge base to test rag but obv once user specific stuff gets implemented each knowledge base will be different
Joseph Stefurak
  7:44 PM
Finished chunks 2 and 4. Heres a summary of whats been added: Devil's Advocate — Today's Progress
RAG Knowledge Base (ChromaDB) — Built a retrieval-augmented generation pipeline that grounds the agent's arguments in real data. Chose ChromaDB over Vertex AI Vector Search or Pinecone because it runs entirely in-process with no external services, zero infra cost, and is safe for Cloud Run's ephemeral filesystem. Designed with a clean abstraction layer (RAGBackend base class) so swapping to Vertex AI RagManagedDb for production is a single env var change.
Per-participant corpus isolation — Each debate session gets its own isolated ChromaDB collection, preventing knowledge bleed between participants. Critical for research study validity. Collections are deleted on session end.
Knowledge base content — Four domain-specific reference files embedded at startup: startup failure patterns, market sizing heuristics, business model benchmarks, and competition dynamics. Retrieved contextually per turn and injected into Gemini before each response.
Google Search grounding — Wired the native Gemini GoogleSearch tool so the agent can cite real competitors, actual funding rounds, and live market data rather than hallucinating statistics.
Revised system prompt — Shifted the agent's framing from pure adversary to critical thinking partner. Added a Challenge/Question mode duality so the agent alternates between attacking weak assumptions directly and asking Socratic questions that force the user to arrive at problems themselves.
Claim tracker — Async background classifier (non-blocking, uses gemini-2.5-flash-lite) that categorizes each user turn as DEFENDED, CONCEDED, NEW_CLAIM, or DEFLECTED with a 1-10 argument strength score. Results surface in a live Argument Tracker UI panel during the debate.
Session debrief report — After ending a debate, generates a structured AI report covering: overall score, verdict, top strengths, critical weaknesses, best moment, biggest gap, and actionable next steps. Displayed as a formatted card on the ended screen.
Graceful interruption — Removed the mic gate that blocked user audio while the agent was speaking. Gemini Live now handles barge-in detection natively. Frontend immediately kills all scheduled audio sources on sc.interrupted and resets the playback timeline.
Audio fix — Replaced the sequential queue approach (which caused click artifacts from JS event loop gaps between chunks) with direct Web Audio API timeline scheduling. Chunks are scheduled back-to-back at the hardware level with no gaps.
Input validation & rate limiting — Added server-side sanitization on claims (500 char limit, control character stripping) and audio chunks (32KB max). Rate limiting on connections (10/min per IP), session starts (5 per socket per 10 min), and audio chunks (200/sec). Silent drop on audio violations, error event emitted for session violations.
Firebase data logging — Full session logging to Firestore via Admin SDK (backend only, no client-side Firebase). Stores transcript, claim events with strength scores, interruption count, and final report. Consent toggle on the frontend — off by default, clearly labeled, data is permanently deleted if session ends without consent.
Python upgrade — Migrated from Python 3.9 (EOL) to 3.11. Switched ChromaDB embedding from SentenceTransformerEmbeddingFunction (required PyTorch) to DefaultEmbeddingFunction (ONNX-based, much lighter dependency chain).
requirements.txt — Generated for the first time with pinned versions for reproducible Cloud Run deploys.
7:45
Rag isnt fully implemented because the prod DB is lowkey a lot of $$ ($0.30/hr/corpus (user)) but I abstracted the functionality so its really easy to plug in later.
Joseph Stefurak
  7:54 PM
As far as breadth goes we're pretty much there for what we need for hackathon and study but were not even close in terms of depth. Need to iron out the details for pretty much every feature and test/experiment extensively. For example the evaluation metrics and debate classification is very inaccurate (which is what well deploy other agents to do).
7:55
Also we need to figure out what we want to do about auth/personalized corpus'. This is particularly difficult to decide which route to go down for a number of reasons that we can go over during our next meeting.
Joseph Stefurak
  8:44 PM
I deployed the current version so that we can test and get an Idea of what/how we want to tweak it
Pinned by
Joseph Stefurak
8:44
https://devils-advocate-488918.web.app/
8:45
Just a warning there are def a million bugs too
8:46
Im hosting backend serverless on cloud run and fronted on firebase
Zaina Qasim
  11:07 AM
Nicely done @Joseph Stefurak! I'll do a deep dive on it over the weekend (lmk if there is something major that you'd like me to pick up). In the mean time, could you share the instructions for hosting? I imagine you'll have to grant permissions/add our accounts to your project.
Zaina Qasim
  11:37 AM
@here On a different note, we should meet sometime tomorrow before class to finalize our abstract/proposal? Would a Zoom call around 12:00 pm work? The submission is due at 2:00pm. From my understanding, here is what remains-
Literature review: @Sean Kraemer Let me know if you need help with this (I could read the VC bench paper, if you'd like to read two more and cite those.)
Rubrics for Judge Agents: @Deji Olaleye Let me know how its coming along and if you need any help, I could work on a quick draft that you could further refine :slightly_smiling_face:
Some other things we should discuss-
Everyone's schedules: how much time each of us can comfortably commit to the project and when.
Expectations for communication: Outside of using Slack, what is everyone comfortable with/expects from the team.
Sean Kraemer
  11:56 AM
yes great job @Joseph Stefurak and good points @Zaina Qasim, sorry for delay on the lit review. will wrap that up this evening. It's a bit hard for me to get work done during the day since i'm working full-time so i'll try to get a lot done this evening. You guys definitely work fast, so thank you for the quick turnarounds on everything!
Zaina Qasim
  4:43 PM
@here I took group 26 cause I'm turning 26 on 03/06- hope you all don't mind :slightly_smiling_face:
Sean Kraemer
  4:44 PM
Gotcha, I just joined group 26 as well
Sean Kraemer
  5:58 PM
lit review notes are currently being added to our google docs, extracting the papers and high level points from the gemini deep research (i've also included a link to the chat sessions in case anyone wants to check that out)
I'll finish adding to that tab, make some edits to the abstract, add the references, and then we can discuss during tomorrow's meeting
Zaina Qasim
  7:18 PM
replied to a thread:
@here On a different note, we should meet sometime tomorrow before class to finalize our abstract/proposal? Would a Zoom call around 12:00 pm work? The submission is due at 2:00pm. From my understanding, here is what remains-…
Great! I've set up a 30 minute meeting for us.
Zaina Qasim is inviting you to a scheduled Zoom meeting.
Topic: CS 568: Finalizing Aabstract/Proposal
Time: Mar 5, 2026 12:00 PM Central Time (US and Canada)
Join Zoom Meeting
https://illinois.zoom.us/j/89982166411?pwd=mG5BAi0W5UDJhXjH0YsDJFiCZhjNfL.1
Meeting ID: 899 8216 6411
Password: 444228
One tap mobile
+13126266799,,89982166411# US (Chicago)
+16513728299,,89982166411# US (Minnesota)
Dial by your location
        +1 312 626 6799 US (Chicago)
        +1 651 372 8299 US (Minnesota)
        +1 786 635 1003 US (Miami)
        +1 929 205 6099 US (New York)
        +1 267 831 0333 US (Philadelphia)
        +1 301 715 8592 US (Washington DC)
        +1 470 250 9358 US (Atlanta)
        +1 470 381 2552 US (Atlanta)
        +1 646 518 9805 US (New York)
        +1 669 900 6833 US (San Jose)
        +1 720 928 9299 US (Denver)
        +1 971 247 1195 US (Portland)
        +1 213 338 8477 US (Los Angeles)
        +1 253 215 8782 US (Tacoma)
        +1 346 248 7799 US (Houston)
        +1 602 753 0140 US (Phoenix)
        +1 669 219 2599 US (San Jose)
        +1 778 907 2071 Canada
        +1 438 809 7799 Canada
        +1 587 328 1099 Canada
        +1 647 374 4685 Canada
        +1 647 558 0588 Canada
        +49 69 7104 9922 Germany
        +49 695 050 2596 Germany
        +44 203 481 5240 United Kingdom
        +44 131 460 1196 United Kingdom
        +44 203 481 5237 United Kingdom
        +81 3 4578 1488 Japan
        +61 8 7150 1149 Australia
        +61 2 8015 6011 Australia
        +61 3 7018 2005 Australia
        +52 554 161 4288 Mexico
Meeting ID: 899 8216 6411
Password: 444228
Find your local number: https://illinois.zoom.us/u/kcLzJlF2D5
Join by SIP
89982166411@zoomcrc.com
Join by H.323
144.195.19.161 (US West)
206.247.11.121 (US East)
221.122.88.195 (Mainland China)
115.114.131.7 (India Mumbai)
115.114.115.7 (India Hyderabad)
159.124.15.191 (Amsterdam Netherlands)
159.124.47.249 (Germany)
159.124.104.213 (Australia Sydney)
159.124.74.212 (Australia Melbourne)
170.114.134.121 (Hong Kong SAR)
64.211.144.160 (Brazil)
159.124.168.213 (Canada Toronto)
159.124.196.25 (Canada Vancouver)
170.114.194.163 (Japan Tokyo)
147.124.100.25 (Japan Osaka)
Meeting ID: 899 8216 6411
Password: 444228
Sean Kraemer
  10:28 AM
Sorry I forgot to mention this, but I might be slightly late to today's meeting because i have a lecture from 11-12:20pm but we usually get out at noon so i think it should be fine, but i'll keep you guys posted.
And then i finished the initial lit review, added notes in the Lit Review Notes tab, and then made an Abstract v2 tab with a few references and some minor refinements/additions to the original draft @Zaina Qasim created. Let's discuss some more at noon, lmk if you have any questions before then, thanks!
Sean Kraemer
  12:04 PM
I'm in the meeting right now, is everyone still good to meet?
Joseph Stefurak
  12:06 PM
https://illinois.zoom.us/j/84079579882?pwd=DG6fOk0bkYuqNKTb3i1bHzxZhpHOaA.1
12:06
We can just use mine for now
Zaina Qasim
  12:50 PM
image.png

image.png
Zaina Qasim
  1:01 PM
@Joseph Stefurak They'll give us $100 in free credits if you fill out a form here: https://docs.google.com/forms/d/e/1FAIpQLSeu0U8YKiLgA3j4hLufXEnBep1YKwPbzrwqKYHt_QqB5Bs7Bg/viewform (edited)
Joseph Stefurak
  2:30 PM
I think I found a good middle-ground that lets us get the functionality that were looking for without having to go the enterprise grade route
2:30
But those credits will be nice bc I already ran through some credits
Zaina Qasim
  2:35 PM
We have a study participant!
Joseph Stefurak
  2:44 PM
Sweet
2:47
Feel free to send the demo to people too if theyre curious: https://devils-advocate-488918.web.app/
2:52
We also got the suggestion to promote this to members from build illinois
Zaina Qasim
  2:52 PM
OOOOO!
There's also iVenture
Joseph Stefurak
  2:53 PM
We got really good feedback how about you guys
2:53
Deji and I were in the same group
Zaina Qasim
  2:53 PM
Ooo what group were you in?
Joseph Stefurak
  2:53 PM
7
Zaina Qasim
  2:53 PM
I want to read. I was in 31
Sean Kraemer
  2:54 PM
Feedback was pretty solid in my room as well, seems to be a common thread of people wondering how the debate will be evaluated.
Deji Olaleye
  2:54 PM
I put them in the google doc so you don't have to zoom in on figma
Joseph Stefurak
  2:57 PM
One of the conversations from just now that someone had with it lol
image.png

image.png
2:58
nvm they apologized were all square
image.png

image.png
2:59
uhhhh idk if these people know we can see the transcript
2:59
I cant even send the last message in here :joy:
Zaina Qasim
  3:00 PM
OML WHAT DOES IT SAY!
Joseph Stefurak
  3:03 PM
No like I actually cant repeat it in the class workspace
3:03
I think I found a bug from how I added data collection too
3:03
So like every convo is recorded for the evaluation bot but then it gets deleted after the debate if they dont consent. But, if they never end the debate and just like close the tab then it never gets deleted
Sean Kraemer
  3:04 PM
Oh i was in group 11 btw, forgot to mention that earlier
Zaina Qasim
  3:05 PM
Lmao we need guardrails. That reminds me though, could you share the details for hosting/add me as a user to your GCP project?
Joseph Stefurak
  3:05 PM
wdym details for hosting
3:05
and yeah Ill add you guys rn
Zaina Qasim
  3:05 PM
Ah if there's anything on my end I'd have to do for deploying to prod etc.
Joseph Stefurak
  3:06 PM
Oh like after you clone the repo?
Zaina Qasim
  3:06 PM
Yeah, wanted to know what instructions you're following so that my pushes don't break things
Joseph Stefurak
  3:07 PM
I havent made any yet thats something I gonna make asap next time I work on it. I dont really have any instructions that Im following
3:07
The only thing would really be adding env vars
3:07
Which is GCP key and FB key
3:07
Which Ill add you guys to rn
3:08
Can you guys send me your google accounts
3:08
like email
Zaina Qasim
  3:08 PM
Its zainaqsm@gmail.com
Deji Olaleye
  3:09 PM
djolaleye@gmail.com
Sean Kraemer
  3:10 PM
seanmkraemer@gmail.com
Joseph Stefurak
  3:11 PM
Im giving you guys owner access just be careful with your keys to not leak them bc the billing is on my credit card
Joseph Stefurak
  3:14 PM
Ok all invites sent out
Sean Kraemer
  3:14 PM
got it, thanks!
Joseph Stefurak
  3:14 PM
Will make a readme this weekend
Joseph Stefurak
  2:42 AM
Final version for the hackathon is live https://devils-advocate-488918.web.app/ . Only thing left is to test for bugs and the submission formalities.
2:43
I added the full user account stuff and personal knowledge base as well as a few other features.
Zaina Qasim
  3:25 PM
This is great! Looks so polished!
Btw, wanted to share a suggestion I received as a work around for the ChromaDB issue-> "You can look into running the ChromaDB docker image on your own infra in order to bypass the costs involved for relying on a hosted version".
Sean Kraemer
  10:36 AM
Just got a chance to use it as well and this looks super clean, great job @Joseph Stefurak!!
Joseph Stefurak
  9:48 PM
Thanks guys. If anyone has time this week it would be huge if you could spend some time trying to break stuff and see if you can find any bugs. I've found a couple already and am gonna go over everything on sunday or monday to get us good to go to submit.
Zaina Qasim
  12:44 PM
@here At some point we should meet up to put together the demo video for the Hackathon. The deadline is Monday, 03/16/2026 at 7 pm CST. I'll put a draft presentation together but lmk when you want to meet (edited)
Sean Kraemer
  2:35 PM
I'm only able to do sunday, ideally in the morning/afternoon
Joseph Stefurak
  2:38 PM
Sunday afternoon works for me
Deji Olaleye
  2:40 PM
Agreed
Zaina Qasim
  12:51 AM
Great! Meeting scheduled as below
Join Zoom Meeting
https://illinois.zoom.us/j/82052428922?pwd=cNFJEwOvqbi0hgpoCTNC08JOMMDdXI.1
Meeting ID: 820 5242 8922
Password: 168362
12:52
Invites sent to your emails as well :slightly_smiling_face:
Zaina Qasim
  11:34 AM
https://docs.google.com/presentation/d/1SB3fwGLSnmXRtiVRUQLDvHuHc4UuRgxtTcEB9fzJkPY/edit?usp=sharing
11:35
https://devpost.com/submit-to/28633-gemini-live-agent-challenge/manage/submissions/957466-devil-s-advocate/project-overview
