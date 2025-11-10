# simple_title Template

This is a built-in SceneWeaver template for creating simple_title scenes.

## Usage

```yaml
scenes:
  - type: template
    name: simple_title
    id: my_simple_title
    with:
      title: 'Example Title'
      duration: 3
```

## Preview

![simple_title preview](screenshot.png)

## Parameters

- `title` (string): The main title text to display (required)
- `duration` (number): Duration in seconds for the scene (optional), default: '3'
- `font` (string): Font family to use (inherited from global settings) (optional), default: 'the global font'
