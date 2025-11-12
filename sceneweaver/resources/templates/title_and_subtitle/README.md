# title_and_subtitle Template

This is a built-in SceneWeaver template for creating title_and_subtitle scenes.

## Usage

```yaml
scenes:
  - type: template
    name: title_and_subtitle
    id: my_title_and_subtitle
    with:
      title: 'Main Title'
      subtitle: 'This is a subtitle example'
      duration: 3
```

## Preview

![title_and_subtitle preview](screenshot.png)

## Parameters

- `title` (string): The main title text to display (required)
- `title_color` (string): Color for the title (optional), default: 'white'
- `title_font` (string): Font for the title (optional)
- `subtitle` (string): The subtitle text (optional)
- `subtitle_color` (string): Color for the subtitle (optional), default: '#cccccc'
- `subtitle_font` (string): Font for the subtitle (optional)
- `duration` (number): Duration in seconds for the scene (optional), default: 'auto'
- `font` (string): Font family to use (inherited from global settings) (optional), default: 'the global font'
