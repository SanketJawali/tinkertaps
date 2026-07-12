# Tinkertaps UI Theme

## Product context

Tinkertaps is a simple web application for working with everyday files.

A user chooses a file, selects what they want to do with it, and receives the resulting file when the work is finished.

Examples include:

- making an image smaller
- changing a file's format
- extracting text from a PDF

The backend may model these operations as asynchronous jobs, workers, queues, and stored objects.

The normal user interface must not expose that mental model.

The user-facing mental model is:

**Choose → change → done**

Tinkertaps is not a file manager, cloud drive, developer tool, or infrastructure dashboard.

---

# Design direction: The quiet desk

The visual direction is inspired by a clean desk in a nearly monochrome room.

Imagine:

- a white desk
- black and grey objects
- generous empty space
- soft natural light
- a plant or a quiet personal object adding a small amount of colour
- a few useful things placed deliberately

The interface is the desk.

Files are things the user briefly places on the desk, changes, and takes away.

The visual result should feel:

- simple
- productive
- quiet
- clean
- approachable

It should not feel futuristic, technical, luxurious, playful, or aggressively branded.

The design is primarily high-contrast grayscale.

Colour is a small accent in the room. It must never take over the interface.

---

# Core design principles

## 1. Use the user's language

Describe what the user wants to do, not how the backend performs it.

Prefer:

- Choose a file
- Make it smaller
- Change the format
- Pull out the text
- Working on it
- Ready
- Download
- Try again
- Your files

Avoid:

- Create job
- Start job
- Process file
- Queue job
- Worker
- Object
- Object key
- Presigned URL
- Processing pipeline
- Asynchronous task

The word `job` may be used internally in code, APIs, database schemas, and developer-facing tools.

It should generally not appear in the normal product interface.

Technical verbs should be replaced with ordinary verbs when the meaning remains clear.

Prefer:

`Make it smaller`

over:

`Compress image`

Prefer:

`Pull out the text`

over:

`Extract text`

Clarity still matters. Do not make language childish or vague simply to avoid technical terms.

---

## 2. One obvious next action

Each page should make the next useful action visually obvious.

Examples:

Landing page:

`Choose a file`

Login:

`Log in`

Register:

`Create account`

File action selection:

`Continue`

Ready file:

`Download`

Failed file:

`Try again`

There should normally be one primary button in a visual region.

Secondary actions use `btn-ghost`, quiet links, or underlined text.

Do not create several equally prominent actions.

---

## 3. Empty space is part of the interface

Do not fill empty areas simply because space is available.

The quiet desk direction depends on restraint.

A page may contain:

- one heading
- one short explanation
- one form

and nothing else.

This is acceptable.

Do not add:

- fake statistics
- testimonial cards
- decorative feature grids
- abstract illustrations
- unnecessary side panels
- random icon boxes

A sparse page is not unfinished when the user's task is clear.

---

## 4. Show meaningful states

When Tinkertaps is working on a file, communicate what the user needs to know.

Recommended user-facing states:

- Uploading
- Waiting
- Working on it
- Ready
- Couldn't finish

More specific language may be used when useful.

Examples:

- Making it smaller
- Changing the format
- Pulling out the text

Do not expose infrastructure states such as:

- queued in Redis
- worker assigned
- object uploaded
- task dispatched

Waiting should feel normal and expected.

Avoid giant loading spinners and fake progress percentages.

Never show a percentage unless the application actually knows the progress.

---

# Colour system

Tinkertaps is fundamentally a grayscale interface.

The base palette should dominate every page.

Approximate visual roles:

| Role | Purpose |
| --- | --- |
| Base 100 | Main white work surface |
| Base 200 | Quiet recessed areas |
| Base 300 | Borders and dividers |
| Base content | Near-black ink |
| Primary | Small visual accent and primary actions |
| Success | Ready and completed states |
| Warning | States requiring attention |
| Error | Failed actions |

The primary accent is a muted oxide red.

It should feel like a single coloured object on a mostly monochrome desk.

It must not turn the interface into a red theme.

Use the primary colour for:

- primary buttons
- small section eyebrows
- active or meaningful details
- keyboard focus
- subtle selection colour

Do not use the primary colour for:

- large backgrounds
- entire sections
- gradients
- heading text
- decorative blobs
- large illustrations

Success remains muted green because green carries useful semantic meaning for completed states.

## DaisyUI colour usage

Prefer semantic DaisyUI classes.

Use:

- `bg-base-100`
- `bg-base-200`
- `border-base-300`
- `text-base-content`
- `text-primary`
- `text-success`
- `text-error`

Avoid fixed Tailwind palette colours such as:

- `bg-white`
- `text-slate-900`
- `bg-red-600`
- `text-green-500`

The theme should control colour globally.

---

# Typography

Typography carries most of the visual identity.

## Interface and body

Use the sans-serif stack defined by `--font-sans`.

Body text should be quiet and highly readable.

Default body copy should use comfortable line height and reduced contrast when secondary.

Example:

```html
<p class="leading-7 text-base-content/60">
```

## Headings

Headings should be:

- compact
- moderately heavy
- tightly tracked
- direct

Typical treatment:

```text
font-semibold
tracking-[-0.035em]
```

Large display headings may use:

```text
tracking-[-0.045em]
leading-[0.98]
```

Do not use thin display fonts or decorative serif fonts.

Do not make every page title enormous.

The oversized typography on the landing page is a deliberate exception.

## Monospace

Use `font-mono` as a small structural signal.

Appropriate uses:

- section eyebrows
- compact stage labels
- file metadata when useful
- IDs in developer-facing interfaces

Example:

```text
YOUR FILE, YOUR WAY
HOW IT WORKS
01 / CHOOSE
```

Monospace text is usually:

- small
- uppercase
- widely tracked

Do not use monospace for:

- paragraphs
- buttons
- form labels
- major headings

---

# Layout

Use centred content widths consistently.

Recommended widths:

- broad marketing pages: `max-w-6xl`
- authentication forms: `max-w-sm`
- focused forms: `max-w-xl` or `max-w-2xl`
- file details: `max-w-4xl`

Standard horizontal page padding:

```text
px-5 lg:px-8
```

Pages should preserve generous negative space on desktop.

Mobile layouts should remain direct and vertically ordered.

Do not preserve desktop composition at the cost of usability on small screens.

---

# Navigation

The main navigation is intentionally small.

The Tinkertaps mark appears on the left.

Contextual account actions appear on the right.

On the landing page:

- Log in
- Get started

On the login page:

- New here?
- Create account

On the register page:

- Already have an account?
- Log in

Navigation copy should reflect the page the user is currently viewing.

Do not show actions that redundantly describe the current page.

The navigation should remain visually quiet.

---

# Buttons

Use DaisyUI button components.

## Primary action

```text
btn btn-primary
```

Examples:

- Choose a file
- Create account
- Log in
- Download

## Secondary action

```text
btn btn-ghost
```

Examples:

- How it works
- Cancel
- Back

## Compact action

```text
btn btn-sm
```

Use for navigation and small actions inside file panels.

## Button rules

Buttons use direct verbs.

Prefer:

`Download`

over:

`Download result file`

Prefer:

`Try again`

over:

`Retry processing job`

Do not use gradients.

Do not add icons when text already makes the action obvious.

Avoid pill-shaped buttons.

---

# Forms

Forms should be narrow, focused, and surrounded by whitespace.

Authentication pages should not use:

- split-screen layouts
- testimonials
- illustrations
- gradient panels
- marketing copy beside the form

A form should ask only for information required at that moment.

Use DaisyUI form and input components consistently.

Example:

```html
<fieldset class="fieldset">
	<label class="fieldset-legend" for="email">
		Email
	</label>

	<input
		id="email"
		type="email"
		class="input w-full"
	/>
</fieldset>
```

Labels should be direct nouns or short instructions.

Examples:

- Name
- Email
- Password
- File
- What do you need?

Placeholder text demonstrates expected input.

It must not replace a label.

Validation errors should appear near the relevant field.

Errors explain:

1. what is wrong
2. how the user can fix it

Avoid vague errors such as:

`Something went wrong`

Prefer:

`That email address doesn't look right. Check it and try again.`

Errors do not apologize.

---

# Surfaces and borders

The interface should feel constructed from flat work surfaces.

Prefer borders over shadows.

Default surface:

```text
bg-base-100
border border-base-300
rounded-box
```

Quiet recessed surface:

```text
bg-base-200/50
```

Shadows should be rare and subtle.

A small shadow may be used when an object needs to visually sit above the work surface.

The landing page file panel is an example.

Do not use:

- large floating SaaS cards
- deep shadows
- glowing borders
- glassmorphism
- backdrop blur as decoration

---

# Radius

The interface uses restrained rounding.

Theme values:

- selectors: `0.4rem`
- fields: `0.4rem`
- boxes: `0.75rem`

Larger feature panels may use `rounded-2xl` when the larger physical scale justifies it.

Avoid excessive pills.

Pills are reserved primarily for compact statuses such as:

- Ready
- Working
- Failed

---

# Signature element: the file progress rail

The recurring visual signature is a thin rail showing meaningful stages in the user's file task.

Example:

```text
● Uploaded
│
● Made smaller
│
● Ready
```

The rail exists because the stages have a meaningful order.

It may appear on:

- landing page examples
- active file views
- file detail pages

The labels should describe what happened to the user's file.

Do not expose backend stages.

Avoid:

```text
● Object uploaded
│
● Worker processing
│
● Output persisted
```

The progress rail must remain visually quiet.

Use:

- thin lines
- small dots
- muted state colours
- short labels

Do not turn it into a large stepper component.

The progress rail should not appear on unrelated pages such as:

- login
- register
- settings

---

# Status badges

Badges communicate compact state.

Recommended mappings:

Waiting:

```text
badge-neutral badge-soft
```

Working:

```text
badge-neutral badge-soft
```

Ready:

```text
badge-success badge-soft
```

Failed:

```text
badge-error badge-soft
```

The exact wording should remain user-facing.

Prefer:

`Working on it`

over:

`Processing`

Prefer:

`Couldn't finish`

over:

`Job failed`

Badges are not decorative labels.

Do not place badges everywhere.

---

# Motion

Motion should acknowledge a meaningful transition.

Allowed:

- one subtle page-entry movement on a major visual
- upload progress
- state transitions
- small button feedback

Avoid:

- floating ambient objects
- animated gradients
- endless card movement
- staggered reveal animations across every section
- decorative particles
- fake loading animations

If the server knows the real state, show the real state.

Respect `prefers-reduced-motion`.

---

# Page guidance

## Landing page

The landing page has one job:

**Help the user understand Tinkertaps and choose a file.**

The hero uses the language:

> Drop it in.  
> Choose what you need.  
> Take the result.

The page demonstrates the file progress rail.

Do not add:

- vanity metrics
- customer logos without real customers
- testimonials without real users
- pricing teasers unless pricing exists
- fake dashboard screenshots

The current landing page structure is:

1. navigation
2. hero and file example
3. three-step explanation
4. final call to action
5. footer

Do not substantially expand this page without a product reason.

---

## Login

The login page is a focused authentication form.

It should contain:

- Welcome back
- short explanation
- email
- password
- forgot password
- Log in
- link to create an account

The page should feel intentionally sparse.

Do not add marketing content to fill the empty space.

---

## Register

The register page is a focused account creation form.

It should contain:

- short introduction
- name
- email
- password
- Create account
- link to log in

Account creation should be framed around the benefit of returning to files later.

Avoid developer-oriented explanations about persistent file history or stored results.

---

## File selection

The file selection page should feel like placing something on the desk.

The primary interaction is choosing or dropping a file.

The drop area should be visually obvious without becoming a giant decorative upload widget.

After a file is selected, show:

- filename
- file size
- relevant file type
- remove or replace action

Then ask what the user wants to do.

Only show actions relevant to the selected file type.

For example, an image may offer:

- Make it smaller
- Change the format

A PDF may offer:

- Pull out the text

Do not show unavailable actions as a huge disabled catalogue.

---

## Active file

The status of the file is the primary information.

Show:

- filename
- current state
- progress rail
- chosen action
- useful timestamps when relevant

Tell the user clearly that they may leave the page if the work continues in the background.

Do not show fake progress percentages.

---

## Ready file

When the result is ready, `Download` is the primary action.

Show useful outcome information when available.

Examples:

- 14.8 MB → 4.2 MB
- 71% smaller
- PNG → WebP

Do not overwhelm the user with internal processing metadata.

---

## Failed file

Explain what could not be completed in ordinary language.

Example:

> We couldn't make this image smaller.

When the user can act:

> Try a different image or try again.

Use `Try again` when retrying is valid.

Do not show raw worker errors or stack traces.

---

## File history

Use `Your files` or `Recent files` in the interface.

Do not use `Job history`.

Prioritise:

1. filename
2. what the user asked Tinkertaps to do
3. status
4. created time
5. result action

Use a table on larger screens when comparing rows is useful.

On small screens, use a stacked list rather than forcing horizontal scrolling for important actions.

Do not lead with vanity statistics.

---

# Writing style

Tinkertaps uses plain, conversational English.

Use active voice.

Keep sentences short.

Interface text should sound like a useful object, not a company salesperson.

Prefer:

`Choose a file`

over:

`Upload your file to get started`

Prefer:

`Your file is ready`

over:

`Your file has been successfully processed`

Prefer:

`We couldn't change this file`

over:

`An unexpected processing error occurred`

Avoid filler words such as:

- seamless
- powerful
- effortless
- revolutionary
- lightning-fast
- intelligent
- next-generation

Do not describe Tinkertaps as an AI product unless a real user-facing feature specifically requires that explanation.

Do not use technical language simply because the implementation is technically interesting.

---

# Anti-patterns

Do not introduce:

- blue-purple gradients
- generic AI product styling
- glassmorphism
- neon-on-black developer tool styling
- warm cream and terracotta editorial styling
- giant gradient blobs
- fake charts
- generic SaaS metric cards
- excessive rounded pills
- huge shadows
- random icon containers
- testimonial panels on auth pages
- decorative dashboard sidebars
- infrastructure terminology
- excessive animation

Do not add a permanent sidebar until the application genuinely has enough primary navigation to justify one.

---

# Consistency checklist

Before considering a page finished, ask:

- Is the next useful action obvious?
- Is there only one dominant action in the current visual region?
- Does the copy describe what the user wants rather than how the backend works?
- Did the word `job` leak into the interface?
- Can a technical verb be replaced with a clearer ordinary verb?
- Is the page still primarily grayscale?
- Is the accent colour being used sparingly?
- Are semantic DaisyUI colours used instead of fixed palette colours?
- Are borders doing work that would otherwise become unnecessary shadows?
- Is monospace limited to small structural information?
- Does every badge communicate a real state?
- Is motion restrained and meaningful?
- Does the mobile layout preserve the order of the user's task?
- Was empty space allowed to remain empty?
- Can any decorative element be removed without losing meaning?

If a decorative element can be removed without losing meaning, remove it.
