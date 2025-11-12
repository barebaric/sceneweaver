# zoom_fade_sequence Template

This is a built-in SceneWeaver template for creating zoom_fade_sequence scenes.

## Usage

```yaml
scenes:
  - type: template
    name: zoom_fade_sequence
    id: my_zoom_fade_sequence
    with:
      animation_duration: 0.4
      transition_duration: 0.25

      # Provide the content for each slide.
      slides:
        - text: 'Rapidly Animating In'
        - text: 'This is the Second Slide'
        - text: 'This is the Third Slide'
          duration: 2
        - text: 'And Finally, the last'

```

## Preview

![zoom_fade_sequence preview](screenshot.png)

## Parameters

- `slides` (list): A list of slide objects. Each object must have 'text' and 'duration' keys. (required)
- `animation_duration` (float): The duration in seconds for the initial zoom and fade-in animation for each slide. (optional), default: '0.3'
- `transition_duration` (float): The duration in seconds for the cross-fade transition between slides. (optional), default: '0.2'
- `font` (string): The font to use for the slide text. Defaults to the global font setting. (optional)
