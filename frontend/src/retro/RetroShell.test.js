import { fireEvent, render, screen } from '@testing-library/react';
import App from '../App';
import io from 'socket.io-client';

jest.mock('socket.io-client', () => jest.fn());

beforeEach(() => {
  window.history.pushState({}, '', '/');
  const socket = {
    handlers: {},
    emit: jest.fn(),
    on: jest.fn((event, handler) => {
      socket.handlers[event] = handler;
    }),
    disconnect: jest.fn(),
  };
  io.mockReturnValue(socket);
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  localStorage.clear();
});

test('shows the retro landing button in the void before the terminal', () => {
  render(<App />);

  expect(
    screen.getByRole('button', { name: 'ENTER MOURNVALE' })
  ).toBeInTheDocument();
  // The terminal stays mounted underneath so the socket can connect.
  expect(screen.getByPlaceholderText('Type your command....')).toBeInTheDocument();
});

test('entering the realms starts the dial-in boot sequence', () => {
  render(<App />);

  fireEvent.click(
    screen.getByRole('button', { name: 'ENTER MOURNVALE' })
  );

  expect(screen.getByRole('button', { name: /SKIP/ })).toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'ENTER MOURNVALE' })
  ).not.toBeInTheDocument();
});

test('escape skips the boot straight into the game', () => {
  render(<App />);

  fireEvent.click(
    screen.getByRole('button', { name: 'ENTER MOURNVALE' })
  );
  fireEvent.keyDown(window, { key: 'Escape' });

  expect(screen.queryByRole('button', { name: /SKIP/ })).not.toBeInTheDocument();
});

test('fullscreen toggle switches modes and persists the choice', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'ENTER MOURNVALE' }));
  fireEvent.keyDown(window, { key: 'Escape' });

  const toggle = screen.getByRole('button', { name: 'Toggle fullscreen' });
  expect(toggle).toHaveTextContent('FULLSCREEN');

  fireEvent.click(toggle);
  expect(localStorage.getItem('retroFullscreen')).toBe('1');
  expect(toggle).toHaveTextContent('WINDOWED');

  fireEvent.click(toggle);
  expect(localStorage.getItem('retroFullscreen')).toBe('0');
  expect(toggle).toHaveTextContent('FULLSCREEN');
});

test('the skip button also ends the boot sequence', () => {
  render(<App />);

  fireEvent.click(
    screen.getByRole('button', { name: 'ENTER MOURNVALE' })
  );
  fireEvent.click(screen.getByRole('button', { name: /SKIP/ }));

  expect(screen.queryByRole('button', { name: /SKIP/ })).not.toBeInTheDocument();
});
