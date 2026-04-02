import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import { FeedbackWidget } from './FeedbackWidget'

function openWidget(props = {}) {
    const user = {
        getIdToken: vi.fn().mockResolvedValue('fake-token'),
    }

    render(
        <FeedbackWidget
            sessionId="session_123"
            user={user}
            consentGiven
            hasReport
            {...props}
        />
    )

    fireEvent.click(screen.getByText(/study feedback/i))
    return { user }
}

function answerScale(prompt, answer = 'Agree') {
    fireEvent.click(screen.getByLabelText(`${prompt} ${answer}`))
}

function completeRequiredFields({ hasReport = true, useOtherHurdle = false } = {}) {
    const ideaPrompts = [
        'The debate helped me refine or improve my business idea.',
        'The debate felt constructive rather than simply tearing my idea down.',
        'I left the debate with clearer next steps for improving the idea.',
    ]
    const voicePrompts = [
        'Speaking with the system felt natural.',
        'It was easy to know when to speak or interrupt.',
        'The voice format made it easy to express my thinking.',
    ]
    const reportPrompts = [
        'The report sections felt well organized.',
        'The report was easy to digest.',
        'The report gave me actionable insights.',
    ]

    ideaPrompts.forEach((prompt) => answerScale(prompt))
    voicePrompts.forEach((prompt) => answerScale(prompt))
    if (hasReport) {
        reportPrompts.forEach((prompt) => answerScale(prompt))
    }

    fireEvent.click(screen.getByLabelText('Voice'))
    if (useOtherHurdle) {
        const hurdleSection = screen.getByText(/what made the voice debate difficult/i).parentElement
        fireEvent.click(within(hurdleSection).getByLabelText('Other'))
        fireEvent.change(screen.getByPlaceholderText(/describe the main issue/i), {
            target: { value: 'Strong accent mismatch in recognition.' },
        })
    } else {
        fireEvent.click(screen.getByLabelText('Nothing major'))
    }
    fireEvent.click(screen.getByLabelText('Live pushback'))
}

describe('FeedbackWidget', () => {
    beforeEach(() => {
        globalThis.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({ ok: true }),
        })
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('shows a consent-off notice instead of a submit form', () => {
        render(
            <FeedbackWidget
                sessionId="session_123"
                user={{ getIdToken: vi.fn() }}
                consentGiven={false}
                hasReport
            />
        )

        expect(screen.getByText(/research feedback unavailable/i)).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: /submit feedback/i })).not.toBeInTheDocument()
    })

    it('skips report questions when no report was generated', () => {
        openWidget({ hasReport: false })

        expect(screen.getByText(/report-specific questions are skipped/i)).toBeInTheDocument()
        expect(screen.queryByText(/the report sections felt well organized/i)).not.toBeInTheDocument()
    })

    it('requires hurdle detail when other is selected', () => {
        openWidget()
        completeRequiredFields({ hasReport: true, useOtherHurdle: false })

        const submitButton = screen.getByRole('button', { name: /submit feedback/i })
        expect(submitButton).toBeEnabled()

        fireEvent.click(screen.getByLabelText('Nothing major'))
        const hurdleSection = screen.getByText(/what made the voice debate difficult/i).parentElement
        fireEvent.click(within(hurdleSection).getByLabelText('Other'))
        expect(submitButton).toBeDisabled()

        fireEvent.change(screen.getByPlaceholderText(/describe the main issue/i), {
            target: { value: 'Needed fallback text support.' },
        })
        expect(submitButton).toBeEnabled()
    })

    it('treats nothing major as exclusive and submits session-linked feedback', async () => {
        const { user } = openWidget()
        completeRequiredFields()

        const nothingMajorButton = screen.getByLabelText('Nothing major')
        const turnTakingButton = screen.getByLabelText('Hard to know when to jump in')

        expect(nothingMajorButton).toHaveAttribute('aria-pressed', 'true')
        fireEvent.click(turnTakingButton)
        expect(nothingMajorButton).toHaveAttribute('aria-pressed', 'false')

        fireEvent.click(screen.getByRole('button', { name: /submit feedback/i }))

        await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1))
        expect(user.getIdToken).toHaveBeenCalledTimes(1)

        const [, request] = globalThis.fetch.mock.calls[0]
        const body = JSON.parse(request.body)

        expect(body.sessionId).toBe('session_123')
        expect(body.feedback.client_context.report_available).toBe(true)
        expect(body.feedback.voice_experience.next_time_preference).toBe('voice')
        expect(body.feedback.voice_experience.hurdles).toEqual(['turn_taking'])
        expect(screen.getByText(/research feedback recorded/i)).toBeInTheDocument()
    })
})
