from dotenv import load_dotenv
load_dotenv()

import asyncio
import re
from session_state import SessionState
from report import generate_report, run_judge

async def with_retry(coro_fn, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            msg = str(e)
            if '429' in msg and attempt < max_retries:
                match = re.search(r'retry in (\d+(?:\.\d+)?)s', msg, re.IGNORECASE)
                delay = float(match.group(1)) if match else 30.0
                print(f"429 quota hit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
            else:
                raise

async def main():
    state = SessionState(user_claim="AI-powered CRM for small businesses")

    fake_turns = [
        ("user", "So our core thesis is that small businesses are completely underserved by existing CRM tools. Salesforce is way too complex, HubSpot is getting expensive, and most SMBs end up just using spreadsheets or nothing at all. What we've built is an AI layer that sits on top of your existing email and calendar and automatically handles follow-ups, pipeline updates, and customer health scoring without any manual data entry."),
        ("agent", "That's a compelling framing but I'd push back on the 'zero setup' claim pretty hard. CRM adoption failure in SMBs isn't primarily a setup problem — it's a behavior change problem. Even if your onboarding takes 5 minutes, you still need the sales rep to actually use the tool consistently. How does your product solve for that, and what does your retention data look like at the 90-day mark?"),
        ("user", "Yeah that's fair, and we've actually thought a lot about that. The reason we think we're different is that because the AI is doing most of the data entry automatically by reading emails and calendar events, the rep doesn't have to change their behavior at all. They just keep doing what they're doing and the CRM updates itself. Our 90-day retention in our pilot cohort is around 74% which we think is strong for this segment."),
        ("agent", "74% retention is okay but not exceptional — Salesforce reports similar numbers for their SMB tier. And the 'AI reads your emails' pitch raises an immediate data privacy red flag for a lot of small business owners, especially in regulated industries like legal, medical, or financial services. How are you handling that objection in the sales process, and are you actually closing deals in those verticals?"),
        ("user", "We're SOC 2 Type 2 compliant, all data is encrypted in transit and at rest, and we give customers full data deletion on request. For regulated industries we have a BAA available. We've closed 3 law firms and a dental practice in our pilot so it's not a blocker so far, though I'll admit our sample size is small and those were warm intros."),
    ] * 100

    for speaker, text in fake_turns:
        state.add_turn(speaker, text)

    print(f"Turn count: {state.turn_count}")
    print(f"Transcript size: {len(state.get_recent_context(n=100))} chars")

    # Sequential with retry — matches production flow
    judge_result = None
    report = None

    print("Running judge...")
    try:
        judge_result = await with_retry(lambda: run_judge(state))
    except Exception as e:
        print(f"Judge failed after retries: {e}")

    print("Running report...")
    try:
        report = await with_retry(lambda: generate_report(state))
    except Exception as e:
        print(f"Report failed after retries: {e}")

    print(f"\njudge_result: {judge_result if judge_result else 'FAILED (None)'}")
    print(f"report: {report if report else 'FAILED (None)'}")

    # Simulate the emit logic
    if judge_result:
        print("✓ judge_result would be emitted")
    else:
        print("✗ judge_result None — judge emit skipped")

    if report:
        print("✓ debate_report would be emitted with payload")
    else:
        print("✓ debate_report would be emitted with None — spinner resolves")

asyncio.run(main())