# Models and media tools

The interface, ASR backend, weights, and media tools are separate. Prepare them before a long recording. The validated primary workflow uses Chinese podcasts on Apple Silicon, MLX Whisper, and large-v3-turbo.

## Match the backend

| Computer | Processing path | Model directory |
| --- | --- | --- |
| Apple Silicon Mac | MLX Whisper; validated Chinese workflow | model/whisper-large-v3-turbo/ |
| Windows | faster-whisper/CTranslate2; separate runtime setup | model/faster-whisper-large-v3-turbo/ |

The default root is ~/Documents/SpeechToTextData/, under the user Documents folder on Windows. Weights belong only in its model/ directory. Repository Downloads/ is temporary reference material, not normal model resolution.

Installers and the pipeline do not download weights. Prepare the exact files manually:

## macOS / MLX Whisper {#macos-mlx-whisper}

Source: [mlx-community/whisper-large-v3-turbo](https://huggingface.co/mlx-community/whisper-large-v3-turbo). Keep these files together:

| Target under the data root | Manual download |
| --- | --- |
| `model/whisper-large-v3-turbo/config.json` | [config.json](https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/config.json?download=true) |
| `model/whisper-large-v3-turbo/weights.safetensors` | [weights.safetensors](https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors?download=true) |

Do not mix the other backend's format or put weights in the source repository.

## Windows / faster-whisper {#windows-faster-whisper}

Source: [h2oai/faster-whisper-large-v3-turbo](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo). Keep these files together:

| Target under the data root | Manual download |
| --- | --- |
| `model/faster-whisper-large-v3-turbo/config.json` | [config.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true) |
| `model/faster-whisper-large-v3-turbo/model.bin` | [model.bin](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true) |
| `model/faster-whisper-large-v3-turbo/preprocessor_config.json` | [preprocessor_config.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true) |
| `model/faster-whisper-large-v3-turbo/tokenizer.json` | [tokenizer.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true) |
| `model/faster-whisper-large-v3-turbo/vocabulary.json` | [vocabulary.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true) |

Do not mix the other backend's format or put weights in the source repository.

## FFmpeg and ffprobe

Both must be discoverable by the CLI doing the work. macOS can use Homebrew:

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

Windows can use an existing PATH installation or vcpkg:

```powershell
vcpkg install "ffmpeg[ffmpeg,ffprobe]:x64-windows"
ffmpeg -version
ffprobe -version
```

Qt Settings can expose the real local vcpkg root. Do not copy another computer's path. Bundled Qt libraries are not media tools.

## Check before ASR

```bash
atot models
atot doctor
atot config set local.asr_model large-v3-turbo
```

Models lists aliases/files; doctor checks the runtime too. A rename cannot turn npz into safetensors or model.bin into MLX weights. Model changes affect future tasks, not existing published text.

## Resources and candidates

Start with the default Chinese workflow. Speed/memory vary with hardware, duration, and backend; there is no universal real-time-factor promise.

Windows CUDA/cuDNN must satisfy the actual CTranslate2 wheel. CUDA 13 alone does not supply explicitly requested CUDA 12 DLLs. Follow the error or select [CPU explicitly](install.md#windows-x64).

Inventory entries include smaller and experimental models. Listing is not promotion, and language choices are not equal validation evidence. Keep research separate from first production setup.

## Moving or updating

Keep weights out of Git. Move model/ with the data root, then verify through the CLI launched against that root. Clearing temporary caches should not delete your weights.

The [inventory](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json) defines aliases, exact files, and manual URLs.

[First transcript →](quick-start.md) · [Missing-model troubleshooting →](guides/troubleshooting.md#model-files-are-missing)
