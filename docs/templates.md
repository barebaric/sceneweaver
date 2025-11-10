# SceneWeaver Templates Overview

This document provides an overview of all built-in SceneWeaver templates.

## Available Templates

### simple_title

A template for creating simple_title scenes

![simple_title](../sceneweaver/resources/templates/simple_title/screenshot.png)

**Usage Example:**

```yaml
scenes:
  - type: template
    name: simple_title
    id: my_simple_title
    with:
      title: 'Example Title'
      duration: 3
```

[View detailed documentation](simple_title/README.md)

---

### slide_sequence

A template for creating slide_sequence scenes

![slide_sequence](../sceneweaver/resources/templates/slide_sequence/screenshot.png)

**Usage Example:**

```yaml
scenes:
  - type: template
    name: slide_sequence
    id: my_slide_sequence
    with:
      slides:
        - text: 'First slide' duration: 2 
        - text: 'Second slide' duration: 2 
        - text: 'Third slide' duration: 2 
```

[View detailed documentation](slide_sequence/README.md)

---

### title_and_subtitle

A template for creating title_and_subtitle scenes

![title_and_subtitle](../sceneweaver/resources/templates/title_and_subtitle/screenshot.png)

**Usage Example:**

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

[View detailed documentation](title_and_subtitle/README.md)

---

