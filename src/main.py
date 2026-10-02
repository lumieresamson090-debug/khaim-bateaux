name: Build APK
on: [push, workflow_dispatch]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: flet-dev/flet-build-action@v1
        id: build
        with:
          target: apk
      - uses: actions/upload-artifact@v4
        with:
          name: K-HAIM-APK
          path: ${{ steps.build.outputs.archive-path }}
