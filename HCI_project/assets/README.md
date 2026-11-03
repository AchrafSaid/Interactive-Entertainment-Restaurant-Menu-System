# OLIVE / TABLE design assets

Source: [HCI Project in Figma](https://www.figma.com/design/YLbjmhkQVvD9lEpkh5qmVf/HCI-Project).

The `figma/` directory contains the original photos and SVG icons returned by
Figma for these screens:

- `3:188610`: interactive menu
- `3:188786`: item detail
- `3:187716`: welcome
- `3:188416`: drinks catalogue
- `3:189005`: order summary

The PNG files beside SVG files are faithful raster exports of the original
icons at double resolution. The application uses these bundled files and makes
no requests to temporary Figma asset URLs. The UI itself is drawn from live
application state, rather than a screenshot of the design.

`fonts/` includes Inter and Lora from the Google Fonts repository, with their
SIL Open Font License texts. Regular and semibold static instances are bundled
so typography stays consistent without installing fonts on the computer.

The existing dessert entries have no supplied food photographs; their cards
use a text placeholder instead of an unrelated food image.
