# SceneWeaver Specification File (`spec.yaml`)

The `spec.yaml` file is the blueprint for your video. It's a declarative file that
defines the global settings and the sequence of scenes that make up the final output.

This document details the structure and all available options for the specification file.

**Table of Contents**

1.  [Top-Level Structure](#top-level-structure)
2.  [The `settings` Block](#the-settings-block)
    - [Using `scene_defaults`](#using-scene_defaults)
3.  [The `scenes` Block](#the-scenes-block)
4.  [Common Scene Attributes](#common-scene-attributes)
    - [Available Effects](#available-effects)
5.  [Scene Types](#scene-types)
    - [Image Scene](#image-scene)
    - [Video Scene](#video-scene)
    - [Video-Images Scene](#video-images-scene)
    - [SVG Scene](#svg-scene)
    - [Template Scene](#template-scene)
6.  [Complete Example](#complete-example)

---

## Top-Level Structure

A SceneWeaver spec file has two primary keys at its root: `settings` and `scenes`.

```yaml
# The main settings for the entire video project.
settings:
  # ... global configuration ...

# A list of scenes that will be rendered in order.
scenes:
  -  # ... first scene ...
  -  # ... second scene ...
```

---

## The `settings` Block

This block defines the global configuration for your video project.

| Key                    | Type    | Description                                                                                       |
| ---------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `width`                | integer | **Required.** The width of the output video in pixels (e.g., `1920`).                             |
| `height`               | integer | **Required.** The height of the output video in pixels (e.g., `1080`).                            |
| `fps`                  | integer | **Required.** The frames per second for the output video (e.g., `30`).                            |
| `output_file`          | string  | **Required.** The path where the final video will be saved (e.g., `output.mp4`).                  |
| `font`                 | string  | The default font for all text annotations. Can be a system font name or a path to a `.ttf` file.  |
| `audio_recording_path` | string  | The sub-directory where newly recorded audio files will be saved. Defaults to `audio`.            |
| `normalization`        | float   | The target volume level for the final video's audio, from `0.0` to `1.0`. Defaults to `0.9`.      |
| `scene_defaults`       | object  | An object containing default attributes that will be applied to every scene in the `scenes` list. |

### Using `scene_defaults`

The `scene_defaults` key is a powerful feature for keeping your specifications DRY
(Don't Repeat Yourself). Any valid scene attribute can be placed here, and it will be
applied to every scene unless that scene explicitly overrides it.

This is especially useful for setting a common transition or cache policy.

**Before `scene_defaults`:**

```yaml
scenes:
  - id: scene_1
    type: image
    image: image1.png
    duration: 5
    transition:
      type: cross-fade
      duration: 1

  - id: scene_2
    type: image
    image: image2.png
    duration: 5
    transition:
      type: cross-fade
      duration: 1
```

**After `scene_defaults`:**

```yaml
settings:
  # ... other settings ...
  scene_defaults:
    transition:
      type: cross-fade
      duration: 1

scenes:
  - id: scene_1
    type: image
    image: image1.png
    duration: 5
    # Transition is inherited automatically

  - id: scene_2
    type: image
    image: image2.png
    duration: 5
    # Transition is inherited automatically
```

---

## The `scenes` Block

This is a list of scene objects. SceneWeaver processes them sequentially to build the final video.

---

## Common Scene Attributes

These attributes can be applied to any scene type.

| Key          | Type              | Description                                                                                                  |
| ------------ | ----------------- | ------------------------------------------------------------------------------------------------------------ |
| `id`         | string            | **Required.** A unique identifier for the scene. Used for caching and targeting scenes via the CLI.          |
| `type`       | string            | **Required.** The type of the scene. Must be one of: `image`, `video`, `video-images`, `svg`, or `template`. |
| `duration`   | number            | The duration of the scene in seconds. Not required if `frames` is set or if the                              |
|              |                   | scene's duration is determined by its audio.                                                                 |
| `frames`     | integer           | The duration of the scene in frames. `duration` is calculated as `frames / settings.fps`.                    |
| `audio`      | list of objects   | A list of audio tracks to play during the scene. Each object can have `file` (path)                          |
|              |                   | and `shift` (in seconds, can be negative).                                                                   |
| `transition` | object            | A transition to play _after_ this scene ends and before the next one begins.                                 |
|              |                   | Specify `type` and `duration`.                                                                               |
| `effects`    | list of objects   | A list of effects to apply to this scene. See "Available Effects" below.                                     |
| `cache`      | boolean or object | Caching policy for this scene. `true` enables caching with default settings. An                              |
|              |                   | object with `max-size` (e.g., `500MB`) provides fine-grained control. `false`                                |
|              |                   | disables it.                                                                                                 |

### Available Effects

The `effects` list accepts objects with a `type` and other parameters.

- **`fade-in` / `fade-out`**: Fades the scene from/to black.

  - `duration` (number, **required**): Duration of the fade in seconds.

  ```yaml
  effects:
    - type: fade-in
      duration: 1.5
  ```

- **`slide-in` / `slide-out`**: Slides the scene into or out of the frame.

  - `duration` (number, **required**): Duration of the slide in seconds.
  - `side` (string, optional): Which side to slide from/to. One of `left`, `right`, `top`, `bottom`. Defaults to `left`.

  ```yaml
  effects:
    - type: slide-in
      duration: 0.5
      side: top
  ```

- **`accel-decel`**: Changes the speed of the clip to fit a new duration, with easing at the start and end.

  - `new_duration` (number, **required**): The target duration for the clip in seconds.
  - `abruptness` (number, optional): How abruptly the speed changes. `1.0` is linear. `> 1` is more abrupt. Defaults to `1.0`.
  - `soonness` (number, optional): When the speed change happens. `1.0` is centered. `> 1` is sooner. Defaults to `1.0`.

  ```yaml
  effects:
    # Make a 5s clip play in 3s with easing
    - type: accel-decel
      new_duration: 3
      abruptness: 1.5
  ```

- **`scroll`**: Scrolls the content of the clip. Useful for taller images.

  - `duration` (number, optional): Sets a new duration for the clip before scrolling.
  - `w`, `h` (integer, optional): The width and height of the "window" to scroll. Defaults to clip's dimensions.
  - `x_speed`, `y_speed` (integer, optional): Speed of scroll in pixels per second.
  - `x_start`, `y_start` (integer, optional): Starting position of the scroll window.

  ```yaml
  effects:
    # Slowly scroll down a tall image over its full duration
    - type: scroll
      y_speed: -50 # pixels per second upwards
  ```

- **`zoom`**: Creates a "Ken Burns" style zoom and pan effect.
  - `duration` (number, optional): Duration of the zoom. Defaults to the clip's full duration.
  - `start_rect` (list, **required**): The starting rectangle `[x, y, width, height]` in percent of the frame.
  - `end_rect` (list, **required**): The ending rectangle `[x, y, width, height]` in percent of the frame.
  ```yaml
  effects:
    # Zoom from full frame into the top-left quadrant over 5 seconds
    - type: zoom
      duration: 5
      start_rect: [0, 0, 100, 100]
      end_rect: [0, 0, 50, 50]
  ```

---

## Scene Types

### Image Scene

Displays a static image. Its duration must be specified with `duration`, `frames`, or
`audio`.

**Specific Attributes:**

| Key           | Type            | Description                                                                     |
| ------------- | --------------- | ------------------------------------------------------------------------------- |
| `image`       | string          | **Required.** Path to the image file.                                           |
| `stretch`     | boolean         | If `true` (default), the image is stretched to fill the screen. If `false`, its |
|               |                 | aspect ratio is preserved.                                                      |
| `position`    | any             | How to position the image when `stretch: false`. Can be `"center"`, `("left",   |
|               |                 | "top")`, or `(x, y)` pixels.                                                    |
| `width`       | number          | When `stretch: false`, resizes the image to a percentage of the screen width    |
|               |                 | (e.g., `80`).                                                                   |
| `height`      | number          | When `stretch: false`, resizes the image to a percentage of the screen height.  |
| `bg_color`    | string          | Background color to show behind a non-stretched image. Defaults to `black`.     |
| `annotations` | list of objects | A list of text or highlight overlays to draw on top of the image.               |

**Example:**

```yaml
- id: image_example
  type: image
  image: assets/screenshot.png
  duration: 8
  stretch: false
  width: 90 # Resize to 90% of screen width, maintaining aspect ratio
  position: center
  annotations:
    - type: text
      content: This is a caption.
      location: bottom
      fontsize: 48
```

### Video Scene

Plays a video file. Its duration is determined by the length of the video file itself.

**Specific Attributes:**

| Key     | Type   | Description                                                                           |
| ------- | ------ | ------------------------------------------------------------------------------------- |
| `file`  | string | **Required.** Path to the video file.                                                 |
| `audio` | list   | If an `audio` track is specified on a video scene, it will **completely replace** the |
|         |        | video's original audio track.                                                         |

**Example:**

```yaml
- id: video_example
  type: video
  file: assets/intro_clip.mp4
  # This narration will replace the audio from intro_clip.mp4
  audio:
    - file: assets/narration.wav
```

### Video-Images Scene

Creates a video from a sequence of image files (e.g., frames of a screen recording).

**Specific Attributes:**

| Key    | Type    | Description                                                                            |
| ------ | ------- | -------------------------------------------------------------------------------------- |
| `file` | string  | **Required.** A glob pattern that matches your image sequence, e.g., `"frames/*.png"`. |
|        |         | Images are sorted naturally.                                                           |
| `fps`  | integer | **Required.** The frame rate at which to play the image sequence.                      |

**Example:**

```yaml
- id: image_sequence_example
  type: video-images
  file: export/frame_*.jpg # Quotes are needed here because of the *
  fps: 24
```

### SVG Scene

Renders an animated SVG file. The SVG file can contain Jinja2 template variables.

**Specific Attributes:**

| Key            | Type   | Description                                                              |
| -------------- | ------ | ------------------------------------------------------------------------ |
| `template`     | string | **Required.** Path to the `.svg` template file.                          |
| `params`       | object | An object of key-value pairs that are passed into the SVG file as Jinja2 |
|                |        | variables, allowing for dynamic, animated graphics.                      |
| `composite_on` | string | The background color to render the (potentially transparent) SVG on      |
|                |        | top of. Defaults to `black`.                                             |

**Example:**

```yaml
- id: svg_example
  type: svg
  template: assets/animated_title.svg
  duration: 5
  params:
    line1: Hello, Animated SVG!
    line2: This text is dynamic.
```

### Template Scene

Uses a pre-defined template, which is a reusable collection of one or more scenes. See the
[Template Documentation](templates.md) for more details.

**Specific Attributes:**

| Key    | Type   | Description                                                                            |
| ------ | ------ | -------------------------------------------------------------------------------------- |
| `name` | string | **Required.** The name of the template to use (e.g., `title_and_subtitle`).            |
| `with` | object | An object of key-value pairs that are passed to the template as parameters, filling in |
|        |        | its Jinja2 variables.                                                                  |

**Example:**

```yaml
- id: template_example
  type: template
  name: title_and_subtitle
  duration: 5
  with:
    title: This is the Main Title
    subtitle: And this is the subtitle
```

---

## Complete Example

Here is a complete `spec.yaml` file demonstrating many of the features together.

```yaml
settings:
  width: 1920
  height: 1080
  fps: 30
  output_file: final_video.mp4
  font: DejaVuSans
  # Apply a cross-fade transition to all scenes by default
  scene_defaults:
    transition:
      type: cross-fade
      duration: 1.5

scenes:
  - id: intro
    type: template
    name: title_and_subtitle
    with:
      title: My Awesome Project
      subtitle: A Demonstration of SceneWeaver
    audio:
      - file: audio/intro_music.mp3

  - id: main_content
    type: image
    image: assets/diagram.png
    duration: 10
    stretch: false
    width: 85
    annotations:
      - type: highlight
        rect: [10, 20, 30, 15] # x, y, w, h in percent
        color: yellow
        opacity: 0.3
      - type: text
        content: Key takeaway shown here
        position: [10, 38] # x, y in percent
        fontsize: 52
    audio:
      - file: audio/narration_part1.wav

  - id: outro_clip
    type: video
    file: assets/logo_reveal.mp4
    # Override the default transition to have no transition
    transition: null
    effects:
      - type: fade-in
        duration: 1
```
