# Contributing to Open Water Platform (OWP)

We want to make contributing to this project as easy and transparent as
possible. Hopefully this document makes the process for contributing clear and
answers any questions you may have. If not, feel free to open an
[Issue](https://github.com/Open-Water-Platform/openwater-platform/issues).

## Issues

We use GitHub issues to track public bugs and requests. Please ensure your bug
description is clear and has sufficient instructions to be able to reproduce the
issue. The best way is to provide a reduced test case on jsFiddle or jsBin.
Consider reading [Issue Template](https://github.com/Open-Water-Platform/openwater-platform/issues/blob/main/ISSUE_TEMPLATE.md) before proceeding.

## Pull Requests

All active development of OWP happens on GitHub. We actively welcome
your [pull requests](https://help.github.com/articles/creating-a-pull-request).

### Considered Changes

Since OWP is a reference implementation of the Open Water Platform spec.
Only changes which comply with this spec will be considered. If you have a 
change in mind which requires a change to the spec, please first open an
[issue](https://github.com/Open-Water-Platform/openwater-platform/issues) against the spec.


### Getting Started

1. Fork this repo by using the "Fork" button in the upper-right

2. Check out your fork

   ```sh
   git clone git@github.com:your_name_here/openwater-platform.git
   ```

3. Install or Update all dependencies

   ```sh
   npm install
   ```

4. Get coding! If you've added code, add tests. If you've changed APIs, update
   any relevant documentation or tests. Ensure your work is committed within a
   feature branch.


## Coding Style

This project uses [Prettier](https://prettier.io/) for standard formatting. To
ensure your pull request matches the style guides, run `npm run prettier`.

- 2 spaces for indentation (no tabs)
- 80 character line length strongly preferred.
- Prefer `'` over `"`
- ES6 syntax when possible. However do not rely on ES6-specific functions to be available.
- Use semicolons;
- Trailing commas,
- Avoid abbreviated words


## License

By contributing to OWP, you agree that your contributions will be
licensed under the [Apache License 2.0](LICENSE).