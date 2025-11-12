# logo_and_text Template

This is a built-in SceneWeaver template for creating logo_and_text scenes.

## Usage

```yaml
scenes:
  - type: template
    name: logo_and_text
    id: logo_and_text
    duration: 1
    with:
      logo_path: logo.png
      text_content: "Your Text Here"

      # The aspect ratio is important for perfect centering.
      # For a 1920x1080 logo, this would be 1920 / 1080 = 1.777
      logo_aspect_ratio: 1

      # Optional overrides:
      logo_height: 30
      gap: 2
      font_size: 100
      bg_color: "#505050"
      text_color: "#ffffff"
      left_offset_percent: 20

```

## Preview

![logo_and_text preview](screenshot.png)

## Parameters

- `bg_color` (string): Optional background color for the scene (e.g., '#333333' or 'blue'). If omitted, the background will be transparent. (optional)
- `logo_path` (string): Path to the logo image file. (required)
- `text_content` (string): The text to display next to the logo. (required)
- `duration` (number): The duration of the scene in seconds. (required)
- `logo_height` (number): The height of the logo as a percentage of the screen height. (optional), default: '40'
- `logo_aspect_ratio` (number): The aspect ratio (width / height) of the logo. (optional), default: '1.0'
- `gap` (number): The gap between the logo and text as a percentage of screen width. (optional), default: '3'
- `font_size` (number): The font size of the text. (optional), default: '90'
- `text_color` (string): The color of the text (e.g., '#ffffff' or 'white'). (optional), default: 'white'
- `left_offset_percent` (number): Offset from the left edge as a percentage of screen width. (optional), default: '0'
