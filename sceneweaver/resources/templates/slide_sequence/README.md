# slide_sequence Template

This is a built-in SceneWeaver template for creating slide_sequence scenes.

## Usage

```yaml
scenes:
  - type: template
    name: slide_sequence
    id: my_slide_sequence
    with:
      slides:
        - text: 'First slide'
          duration: 2 
        - text: 'Second slide'
          duration: 2 
        - text: 'Third slide'
          duration: 2 

```

## Preview

![slide_sequence preview](screenshot.png)

## Parameters

- `slides` (array): Array of slide objects, each containing: (required)
  - `text` (string): Text content for the slide (required)
  - `duration` (number): Duration in seconds for this slide (required), default: 2
- `font` (string): Font family to use (inherited from global settings) (optional), default: 'the global font'
