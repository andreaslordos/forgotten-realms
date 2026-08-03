import { act, fireEvent, render, screen } from '@testing-library/react';
import BootSequence from './BootSequence';

async function advanceToTitleCard() {
  for (let step = 0; step < 150; step += 1) {
    await act(async () => {
      jest.runOnlyPendingTimers();
      await Promise.resolve();
    });
  }
}

beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});

test('waits for key release before leaving the title card', async () => {
  const onDone = jest.fn();
  render(<BootSequence reduced onDone={onDone} />);
  await advanceToTitleCard();

  expect(screen.getByText('PRESS ANY KEY')).toBeInTheDocument();

  fireEvent.keyDown(window, { key: 'Enter' });
  expect(onDone).not.toHaveBeenCalled();

  fireEvent.keyUp(window, { key: 'Enter' });
  expect(onDone).toHaveBeenCalledTimes(1);
});
