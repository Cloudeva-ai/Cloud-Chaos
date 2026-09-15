# Design and motion assets

The registration, game and results/leaderboard concept PNGs record the visual direction generated during this redesign. The implementation retains the original Cloudeva logo and questions. Final mascot placement follows the subsequent request: the original cool character floats above the starting form; the waving character accompanies the post-quiz Cloudeva registration invitation.

## Shipped assets

- `static/mascot_cool_cutout.png`: original supplied relaxing mascot, animated with a slow CSS float.
- `static/mascot-wave-sheet.png`: generated 4-by-4 animation artwork using the supplied mascot as the visual reference.
- `static/mascot-wave-smooth.webm`: transparent VP9 clip, 320x320, 30fps, about 4.6 seconds and 390KB. FFmpeg assembles the artwork and interpolates color motion to 30fps, with separately interpolated alpha and a short rest at each end. This is generated frame artwork with interpolation, not a native generative video model output.
- `static/mascot-idle.png`: first-frame poster for the video.
- `static/fonts/`: self-hosted Manrope weights and their OFL license.

The shipped video does not need an API or generation service at runtime. The header motion control pauses video and CSS animation; the initial state honors the system reduced-motion preference. The gift hamper prize image and external registration destination are retained.

## Theme

Navy `#0b202b` and `#023c57`, teal `#06c2ac`, mint `#72e0ca`, text `#f1f7f8`. Layout uses a wide two-column starting screen and a narrower question/results surface. The mobile view stacks the starting screen and keeps Right/Wrong choices side by side. Typography, fine borders, brief card entry transitions and restrained background glow carry the visual treatment.
