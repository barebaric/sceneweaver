# SceneWeaver

SceneWeaver is a command-line tool for creating videos from a declarative YAML specification.
Under the hood, it uses MoviePy to render and assemble scenes, allowing for repeatable and
version-controllable video production.

For larger projects it supports modular composition and caching, and you can include other
videos as well.

| Feature                                | Description                                                                |
| :------------------------------------- | :------------------------------------------------------------------------- |
| **Declarative YAML Configuration**     | Define videos in a version-controllable YAML specification.                |
| **Scene-Based Composition**            | Compose videos from modular scenes (images, video clips, templates, etc.). |
| **Dynamic SVG Templates**              | Generate complex, animated graphics using templated SVG files.             |
| **Intelligent Caching**                | Automatically caches rendered scenes, only re-rendering what has changed.  |
| **Interactive CLI Tool**               | Interactive CLI for creating specs, adding scenes, and recording audio.    |
| **Audio Integration & Recording**      | Add audio tracks to scenes; includes a built-in recorder.                  |
| **Annotations, Transitions & Effects** | Apply text annotations, transitions, and video effects.                    |

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

#### Managing Scenes

SceneWeaver provides interactive commands to help you build your spec file quickly.

- **Add a new scene:**

  ```bash
  # Interactively prompts for ID, type, and required info
  sceneweaver scene add my_video.yaml

  # Directly specify the new scene's ID and type
  sceneweaver scene add my_video.yaml:new_intro image
  ```

- **Record audio for a scene:**

  ```bash
  # Interactively prompts to select a scene to record for
  sceneweaver scene audio my_video.yaml

  # Directly target a scene by its ID
  sceneweaver scene audio my_video.yaml:main_image
  ```

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

#### Using SVG Templates

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
