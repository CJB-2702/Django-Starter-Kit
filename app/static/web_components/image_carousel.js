/**
 * Image carousel web component that displays images in a horizontal scrollable layout.
 * Accepts images via slots and provides left/right navigation.
 * Default preview dimensions: 300x300px.
 *
 * Usage:
 * <image-carousel preview-height="250" preview-width="400">
 *   <img src="...">
 *   <img src="...">
 * </image-carousel>
 */
class ImageCarousel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._currentIndex = 0;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .carousel-container {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        .carousel-viewer {
          flex: 1;
          display: flex;
          justify-content: center;
          background-color: #f5f5f5;
          border: 1px solid #dbdbdb;
          overflow: hidden;
        }
        ::slotted(img) {
          max-width: 100%;
          max-height: 100%;
          display: block;
          object-fit: contain;
        }
        .counter {
          white-space: nowrap;
          flex-shrink: 0;
          font-size: 0.875rem;
          color: #7a7a7a;
        }
      </style>
      <div class="carousel-container">
        <button class="button is-small is-light" part="prev-button" aria-label="Previous image">‹</button>
        <div class="carousel-viewer">
          <slot></slot>
        </div>
        <button class="button is-small is-light" part="next-button" aria-label="Next image">›</button>
        <div class="counter"><span class="current">1</span> / <span class="total">1</span></div>
      </div>
    `;
  }

  connectedCallback() {
    const previewHeight = this.getAttribute("preview-height") || "300";
    const previewWidth = this.getAttribute("preview-width") || "300";

    const viewer = this.shadowRoot.querySelector(".carousel-viewer");
    viewer.style.width = `${previewWidth}px`;
    viewer.style.height = `${previewHeight}px`;

    const prevButton = this.shadowRoot.querySelector('[part="prev-button"]');
    const nextButton = this.shadowRoot.querySelector('[part="next-button"]');

    prevButton.addEventListener("click", () => this.prev());
    nextButton.addEventListener("click", () => this.next());

    const slot = this.shadowRoot.querySelector("slot");
    const updateImages = () => {
      this._updateImageVisibility();
      this._updateCounter();
      this._updateButtonStates();
    };

    slot.addEventListener("slotchange", updateImages);
    updateImages();

    const observer = new MutationObserver(updateImages);
    observer.observe(this, { childList: true, subtree: true });
  }

  _getImages() {
    const slot = this.shadowRoot.querySelector("slot");
    return slot.assignedElements({ flatten: true }).filter((el) => el.tagName === "IMG");
  }

  _updateImageVisibility() {
    const images = this._getImages();
    images.forEach((img, i) => {
      img.style.display = i === this._currentIndex ? "block" : "none";
    });
  }

  _updateCounter() {
    const images = this._getImages();
    const current = this.shadowRoot.querySelector(".current");
    const total = this.shadowRoot.querySelector(".total");
    current.textContent = images.length > 0 ? this._currentIndex + 1 : 0;
    total.textContent = images.length;
  }

  _updateButtonStates() {
    const images = this._getImages();
    const prevButton = this.shadowRoot.querySelector('[part="prev-button"]');
    const nextButton = this.shadowRoot.querySelector('[part="next-button"]');

    prevButton.disabled = this._currentIndex === 0;
    nextButton.disabled = this._currentIndex === images.length - 1;
  }

  prev() {
    if (this._currentIndex > 0) {
      this._currentIndex--;
      this._updateImageVisibility();
      this._updateCounter();
      this._updateButtonStates();
      this.dispatchEvent(new CustomEvent("carousel-change", { detail: { index: this._currentIndex } }));
    }
  }

  next() {
    const images = this._getImages();
    if (this._currentIndex < images.length - 1) {
      this._currentIndex++;
      this._updateImageVisibility();
      this._updateCounter();
      this._updateButtonStates();
      this.dispatchEvent(new CustomEvent("carousel-change", { detail: { index: this._currentIndex } }));
    }
  }
}

if (!customElements.get("image-carousel")) {
  customElements.define("image-carousel", ImageCarousel);
}
