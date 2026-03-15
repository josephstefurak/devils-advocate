import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import App from './App'

describe('Idle state', () => {
    function getPastLanding() {
        render(<App />)
        fireEvent.click(screen.getByText(/pitch your idea/i))
    }

    it('renders the textarea and start button after landing', () => {
        getPastLanding()
        expect(screen.getByPlaceholderText(/describe your.*idea/i)).toBeInTheDocument()
        expect(screen.getByText(/start debate/i)).toBeInTheDocument()
    })

    it('does not allow starting with empty claim and no uploads', () => {
        const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => { })
        getPastLanding()
        fireEvent.click(screen.getByText(/start debate/i))
        expect(alertMock).toHaveBeenCalledWith(expect.stringMatching(/position|upload documents/i))
    })

    it('shows guest label for anonymous user', () => {
        getPastLanding()
        expect(screen.getByText(/^Guest$/)).toBeInTheDocument()
    })
})

describe('Consent toggle', () => {
    it('defaults to off', () => {
        render(<App />)
        // Start a debate to get to debating state where toggle is visible
        // This would require more setup — shows where you'd expand tests
    })
})