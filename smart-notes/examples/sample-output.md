# Synthetic example — Gradient descent

[Watch video](https://www.youtube.com/watch?v=DEMO0000001) · Offline test fixture; not a real lecture · 01:30

Captions: user-provided · Source language: en · Note language: en · Coverage: complete

Visual inspection: Transcript-only offline fixture. No video or screenshots were inspected.

## Evidence limitations

- Synthetic fixture: the video ID and captions are invented. Links demonstrate formatting and do not identify a source lecture.
- Visual unavailable at 00:46: Offline synthetic fixture; there is no video to capture.
- No key frames retained; the notes contain no screenshot evidence.

## Overview

This synthetic lesson introduces gradient descent: use the gradient of an objective to choose a local update, then scale that update with a learning rate.

## 1. Objective and gradient

[00:00–00:30](https://www.youtube.com/watch?v=DEMO0000001&t=0s)

The optimization problem is to find a parameter value that minimizes an objective. For a differentiable objective, the gradient indicates the local direction of steepest increase.

### Definitions

- $\theta$: parameter being optimized.
- $J(\theta)$: objective to minimize.
- Gradient: local direction of steepest increase.

## 2. Update rule and worked step

[00:30–01:14](https://www.youtube.com/watch?v=DEMO0000001&t=30s)

Subtract a positive learning rate times the current gradient. The worked one-dimensional example evaluates the derivative first, then applies the update.

### Definitions

- $\alpha$: positive learning rate.

### Important equations

$$
\theta_{k+1}=\theta_k-\alpha\nabla J(\theta_k)
$$

$$
J(\theta)=\theta^2,\qquad J'(\theta)=2\theta
$$

### Worked examples

1. Start at $\theta_0=2$ with $\alpha=0.1$.
2. Evaluate the derivative: $J'(2)=4$.
3. Update: $\theta_1=2-0.1(4)=1.6$.

### Added explanations (not attributed to the speaker)

- As a supplementary check, the objective falls from $J(2)=4$ to $J(1.6)=2.56$. These objective values are computed here, not spoken in the fixture.

## 3. Learning rate

[01:14–01:30](https://www.youtube.com/watch?v=DEMO0000001&t=74s)

A learning rate that is too large can overshoot. The appropriate scale depends on the objective's shape.

### Common mistakes

- Assuming that increasing the learning rate always improves progress.

### Uncertainties

- The fixture does not provide a general step-size bound or convergence guarantee.

## Key concepts

- The gradient sets a local direction; the learning rate controls how far to move.

## Review points (generated study aids)

- Reproduce the update from 2 to 1.6 without looking at the worked example.
- Why does the gradient descent update subtract the gradient?

## Timeline

- [00:00](https://www.youtube.com/watch?v=DEMO0000001&t=0s) — Objective and gradient
- [00:30](https://www.youtube.com/watch?v=DEMO0000001&t=30s) — Update rule and worked step
- [01:14](https://www.youtube.com/watch?v=DEMO0000001&t=74s) — Learning rate
