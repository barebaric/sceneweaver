# Using SVG and Animations

For creating complex, animated graphics or title cards, you can use the `svg`
scene type. This scene renders an SVG file for every frame, allowing you to create
dynamic animations by parameterizing the SVG's attributes.

It uses the [Jinja2](https://jinja.palletsprojects.com/) templating language, which
gives you access to special variables inside your SVG file.

**Example YAML:**

```yaml
- id: animated_intro
  type: svg
  duration: 5
  # The path to your SVG file, relative to the spec
  template: templates/my_card.svg
  # Parameters to be passed into the template
  params:
    main_title: "SVG is Powerful"
    accent_color: "tomato"
```

**Available Jinja2 Variables in your SVG:**
Your SVG template has access to all keys from the `params` block, as well as these
special variables for creating animations:

- `progress`: A float from `0.0` to `1.0` representing the scene's completion.
- `timestamp`: The current time in seconds (e.g., `2.5`).
- `duration`: The total duration of the scene in seconds.
- `frame`: The current frame number.
- `min()`, `max()`, `round()`: Useful functions for calculations.

**Example `my_card.svg`:**
You can use these variables to dynamically change any attribute in your SVG file.

```xml
<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
    <!-- Use a parameter for the stroke color -->
    <rect x="360" y="400" width="1200" height="300"
          stroke="{{ accent_color }}" stroke-width="5" rx="15"

          <!-- Use 'progress' to animate the opacity from 0 to 1 -->
          opacity="{{ min(1, progress / 0.2) }}"
    />

    <!-- Use another parameter for the text content -->
    <text x="960" y="550" font-size="90" text-anchor="middle" fill="white">
        {{ main_title }}
    </text>
</svg>
```
