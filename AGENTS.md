# Repository Guidelines

## Project Name

The project's Chinese name is **地理故事工坊**. Its English name is **Geo Story Studio**.

The confirmed content series is **认识宇宙**. Keep its current production and candidate topics in `docs/content-series.md`.

The user-provided geography textbook library is `/Users/huyin/Desktop/Niki/教材/地理`. Read relevant local textbooks and atlases directly before asking for textbook materials again. Preserve these source PDFs; record actual pages, publisher, edition when present, and file hashes. See `docs/material-library.md` for the inventory and verified page mapping.

This project produces **silent videos only**, as confirmed by the user on 2026-10-23. A continuous MP4 with readable timed captions, checked visuals, covers, and publication copy is the intended video deliverable. Voiceover is not required and must not be treated as unfinished work or an environmental blocker. Interpret historical `awaiting_audio` / `waiting_for_audio` fields as legacy metadata when reporting silent-video completion. Final publication approval remains a separate step.

Keep deliverables from the same skill run together under the work's build version directory, with final files in `outputs/` and previews in `preview/`.

Every Douyin work also needs landscape 4:3 and portrait 3:4 covers, an upload title, a description, exactly 30 distinct relevant keywords, and suggested hashtags. Put all publication text in one UTF-8 file, `outputs/发布文案.txt`, with sections for title, description, keywords, and hashtags. Put all 30 keywords on one line, separated by commas (`,`); see `skills/douyin-build/references/upload-package-contract.md`.

Douyin collection covers use a square 1080×1080 canvas, per the user's preference confirmed on 2026-10-18.

## Project Structure & Module Organization

This repository is currently a clean starting point with no source files or established directory layout. As the project grows, keep application code in `src/`, automated checks in `tests/`, and static files in `assets/` (or the framework’s standard public directory). Group related code by feature and keep configuration at the repository root. Update this guide when the actual structure is established.

## Build, Test, and Development Commands

No build system or package manifest is present yet, so there are no repository-specific commands to run. When adding a toolchain, define the standard local run, build, and test commands in its manifest (for example, `npm run dev`, `npm run build`, and `npm test`) and document any required setup in the README. Run the relevant checks before submitting changes.

## Coding Style & Naming Conventions

Follow the formatter and lint rules configured for the language or framework once introduced; avoid adding competing style tools. Use clear, descriptive names, keep modules focused, and match existing file naming patterns. Prefer small changes that are easy to review. If a convention is not yet established, choose one consistently and record it in project configuration.

## Testing Guidelines

No test framework or tests are present yet. Add tests alongside the first meaningful behavior, use descriptive names that state the behavior under test, and provide a single documented command for running the suite. Include regression coverage when fixing a bug.

## Commit & Pull Request Guidelines

Git history is not available in this directory, so no existing commit convention could be identified. Use concise imperative commit subjects, such as `Add map layer controls`. Pull requests should explain the change and its motivation, list validation performed, link related issues when available, and include screenshots for visible UI changes.

## Security & Configuration

Keep credentials and local secrets out of version control. Provide safe examples in a checked-in `.env.example` if environment variables are introduced, and document required configuration without including real secret values.
