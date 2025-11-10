# SceneWeaver

SceneWeaver is a command-line tool for creating videos from a declarative YAML specification.
Under the hood, it uses MoviePy to render and assemble scenes, allowing for repeatable and
version-controllable video production.

For larger projects it supports modular composition and caching, and you can include other
videos as well.

| Feature                                   |                                                                               |
| :---------------------------------------- | ----------------------------------------------------------------------------- |
| ✅ **Re-usable Templates**                | Check the [template library](docs/templates.md) for a gallery.                |
| ✅ **Animated SVGs**                      | Generate complex, animated graphics using [templated SVG files](docs/svg.md). |
| ✅ **Repeatable Production**              | Define videos in a version-controllable [YAML specification](docs/specs.md).  |
| ✅ **Scene-Based Composition**            | Compose videos from modular scenes (images, video clips, templates, etc.).    |
| ✅ **Intelligent Caching**                | Automatically caches rendered scenes, only re-rendering what has changed.     |
| ✅ **Interactive CLI Tool**               | Interactive CLI for creating specs, adding scenes, and recording audio.       |
| ✅ **Audio Integration & Recording**      | Add audio tracks to scenes; includes a built-in recorder.                     |
| ✅ **Annotations, Transitions & Effects** | Apply text annotations, transitions, and video effects.                       |

## Installation

```bash
sudo apt install ffmpeg portaudio19-dev     # Ubuntu 24.04. May be different on other distros
pip install sceneweaver
```

## Usage

### Starting

First, create a new specification file to define your video's structure.

```bash
sceneweaver create my_video.yaml    # creates a new template you can edit
sceneweaver generate my_video.yaml
```

### Example specification

Here is a basic example of a `my_video.yaml` file:

```yaml
settings:
  width: 1920
  height: 1080
  fps: 30
  output_file: "output.mp4"

scenes:
  - id: intro_card
    type: template
    name: title_and_subtitle
    with:
      title: Hello, SceneWeaver!
      subtitle: Using a built-in template
    audio: my/narration.wav
    transition:
      type: cross-fade
      duration: 1

  - id: main_image
    type: image
    duration: 10
    image: "~/path/to/your/image.png"
    stretch: false # Preserves aspect ratio
    width: 80 # As 80% of the screen width
    annotations:
      - type: text
        location: bottom
        content: This is a caption for the image.
    cache:
      max-size: "2GB"
    transition:
      type: cross-fade
      duration: 2

  - id: outro
    type: video
    file: something.mp4
    effects:
      - type: fade-out
        duration: 1
```

### Other Commands

#### Rendering and Cache

- **Render a single scene** (for quick previews):

  ```bash
  sceneweaver generate my_video.yaml:intro_card
  ```

- **Force re-rendering** (ignoring the cache):

  ```bash
  sceneweaver generate my_video.yaml --force
  ```

- **Clear the cache** of all previously rendered scenes:
  ```bash
  sceneweaver clean
  ```

#### Managing Scenes

- **Interactively add a new scene** to your spec file. It will prompt for the scene type and required details.

  ```bash
  sceneweaver scene add my_video.yaml
  ```

- **Add a new `image` scene non-interactively** with a specific ID (`new_intro`).

  ```bash
  sceneweaver scene add my_video.yaml:new_intro image
  ```

- **Record audio for a scene.** It will prompt you to select which scene from the file.

  ```bash
  sceneweaver scene audio my_video.yaml
  ```

- **Directly record audio** for the scene with the ID `main_image`.
  ```bash
  sceneweaver scene audio my_video.yaml:main_image
  ```

#### Managing Templates

- **List all available** built-in and user-created templates.

  ```bash
  sceneweaver template list
  ```

- **Show details about a specific template**, including its parameters and a usage example.

  ```bash
  sceneweaver template info title_and_subtitle
  ```

- **Create a new, empty user template** in your local configuration directory, ready for you to customize.
  ```bash
  sceneweaver template create my_custom_title
  ```

## Development

This project uses [Pixi](https://pixi.sh/) for environment and task management.

- **Setup the environment:**

  ```bash
  pixi install
  ```

- **Run the app:**

  ```bash
  pixi run sceneweaver my_template.yaml
  ```

- **Common tasks** (run with `pixi run <task>`):
  - `test`: Run the test suite.
  - `lint`: Run all linters (flake8, pyflakes, pyright).
  - `format`: Format the code using Ruff.
