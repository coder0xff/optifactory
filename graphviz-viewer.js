/**
 * GraphvizViewer - Reusable Vue component for interactive SVG graph viewing
 * Provides zoom and pan functionality for Graphviz-rendered graphs
 */
import { Graphviz } from 'https://cdn.jsdelivr.net/npm/@hpcc-js/wasm-graphviz@1.13.0/+esm';

// Lazy-load graphviz instance (shared across all components)
let graphvizInstance = null;
async function getGraphviz() {
    if (!graphvizInstance) {
        graphvizInstance = await Graphviz.load();
    }
    return graphvizInstance;
}

const GraphvizViewerComponent = {
    template: `
        <div class="graphviz-viewer">
            <div 
                v-if="dotSource"
                class="viewer-container"
                ref="viewerContainer"
                @mousedown="startPan"
                @mousemove="handlePan"
                @mouseup="endPan"
                @mouseleave="endPan"
                @wheel="handleZoom"
            >
                <div class="viewer-content">
                    <div 
                        ref="svgContainer" 
                        class="viewer-svg"
                    ></div>
                </div>
            </div>
            <div v-else class="viewer-placeholder">
                {{ placeholder }}
            </div>
            <div v-if="dotSource" class="zoom-indicator">
                <button @click="zoomToFit" class="zoom-fit-button">Fit</button>
                <span>{{ (zoomFactor * 100).toFixed(0) }}%</span>
            </div>
        </div>
    `,
    props: {
        dotSource: {
            type: String,
            default: null
        },
        placeholder: {
            type: String,
            default: 'Graph visualization will appear here'
        }
    },
    emits: ['statusChange'],
    data() {
        return {
            zoomFactor: 1.0,
            isPanning: false,
            panStartX: 0,
            panStartY: 0,
            scrollStartX: 0,
            scrollStartY: 0,
            svgNaturalWidth: 0,
            svgNaturalHeight: 0
        };
    },
    watch: {
        zoomFactor() {
            this.applySvgZoom();
        },
        dotSource: {
            handler(newSource) {
                if (newSource) {
                    this.renderGraphviz(newSource);
                }
            },
            immediate: true
        }
    },
    methods: {
        /**
         * Render DOT string to SVG using @hpcc-js/wasm
         * @param {string} dotSource - Graphviz DOT source string
         */
        async renderGraphviz(dotSource) {
            if (!dotSource) return;
            
            // Wait for next tick to ensure DOM is updated
            await this.$nextTick();
            
            const container = this.$refs.svgContainer;
            if (!container) {
                console.warn('SVG container ref not found');
                return;
            }
            
            try {
                // Get graphviz instance and render DOT to SVG
                const graphviz = await getGraphviz();
                const svg = await graphviz.layout(dotSource, 'svg', 'dot');
                container.innerHTML = svg;
                
                // Update SVG dimensions for zoom calculations
                this.updateSvgDimensions();
                
                // Reset zoom to 100% when new diagram is rendered
                this.zoomFactor = 1.0;
                
                // Emit status
                this.$emit('statusChange', { 
                    text: `Zoom: ${(this.zoomFactor * 100).toFixed(0)}%`, 
                    level: 'info' 
                });
                
                return true;
            } catch (error) {
                console.error('Graphviz rendering error:', error);
                this.$emit('statusChange', { 
                    text: 'Graph rendering failed: ' + error.message, 
                    level: 'error' 
                });
                return false;
            }
        },
        
        /**
         * Handle mouse wheel zoom event
         * Zooms centered on mouse cursor position
         */
        handleZoom(event) {
            event.preventDefault();
            
            const container = this.$refs.viewerContainer;
            if (!container) return;
            
            // Get mouse position relative to container
            const rect = container.getBoundingClientRect();
            const mouseX = event.clientX - rect.left;
            const mouseY = event.clientY - rect.top;
            
            // Get scroll position before zoom
            const scrollX = container.scrollLeft;
            const scrollY = container.scrollTop;
            
            // Calculate zoom delta (1.1^1 per wheel notch, matching Python)
            const delta = event.deltaY > 0 ? -1 : 1;
            const oldZoom = this.zoomFactor;
            const zoomChange = Math.pow(1.1, delta);
            
            // Clamp zoom between 0.35x and 2.0x (matching Python's -10 to 7 range)
            this.zoomFactor = Math.max(0.35, Math.min(2.0, this.zoomFactor * zoomChange));
            
            // Wait for size changes to apply, then adjust scroll position
            this.$nextTick(() => {
                const zoomRatio = this.zoomFactor / oldZoom;
                container.scrollLeft = scrollX * zoomRatio + (mouseX * (zoomRatio - 1));
                container.scrollTop = scrollY * zoomRatio + (mouseY * (zoomRatio - 1));
                
                // Emit status
                this.$emit('statusChange', { 
                    text: `Zoom: ${(this.zoomFactor * 100).toFixed(0)}%`, 
                    level: 'info' 
                });
            });
        },
        
        /**
         * Start panning operation
         */
        startPan(event) {
            this.isPanning = true;
            this.panStartX = event.clientX;
            this.panStartY = event.clientY;
            const container = this.$refs.viewerContainer;
            if (container) {
                this.scrollStartX = container.scrollLeft;
                this.scrollStartY = container.scrollTop;
            }
        },
        
        /**
         * Handle pan movement
         */
        handlePan(event) {
            if (!this.isPanning) return;
            
            const container = this.$refs.viewerContainer;
            if (!container) return;
            
            const deltaX = event.clientX - this.panStartX;
            const deltaY = event.clientY - this.panStartY;
            
            container.scrollLeft = this.scrollStartX - deltaX;
            container.scrollTop = this.scrollStartY - deltaY;
        },
        
        /**
         * End panning operation
         */
        endPan() {
            this.isPanning = false;
        },
        
        /**
         * Reset zoom to 100%
         */
        resetZoom() {
            this.zoomFactor = 1.0;
        },
        
        /**
         * Update stored SVG natural dimensions
         */
        updateSvgDimensions() {
            const svgContainer = this.$refs.svgContainer;
            if (!svgContainer) return;
            
            const svg = svgContainer.querySelector('svg');
            if (!svg) return;
            
            const viewBox = svg.viewBox.baseVal;
            this.svgNaturalWidth = viewBox.width || svg.width.baseVal.value;
            this.svgNaturalHeight = viewBox.height || svg.height.baseVal.value;
            
            this.applySvgZoom();
        },
        
        /**
         * Apply current zoom factor to SVG element
         */
        applySvgZoom() {
            const svgContainer = this.$refs.svgContainer;
            if (!svgContainer) return;
            
            const svg = svgContainer.querySelector('svg');
            if (!svg || !this.svgNaturalWidth || !this.svgNaturalHeight) return;
            
            // Set the SVG size directly (this affects both layout and visual)
            svg.setAttribute('width', this.svgNaturalWidth * this.zoomFactor);
            svg.setAttribute('height', this.svgNaturalHeight * this.zoomFactor);
        },
        
        /**
         * Zoom to fit the entire diagram in the viewport
         */
        zoomToFit() {
            const container = this.$refs.viewerContainer;
            const svgContainer = this.$refs.svgContainer;
            if (!container || !svgContainer) return;
            
            const svg = svgContainer.querySelector('svg');
            if (!svg) return;
            
            // Get viewport dimensions
            const viewportWidth = container.clientWidth;
            const viewportHeight = container.clientHeight;
            
            // Get SVG's natural dimensions
            const viewBox = svg.viewBox.baseVal;
            const svgWidth = viewBox.width || svg.width.baseVal.value;
            const svgHeight = viewBox.height || svg.height.baseVal.value;
            
            // Account for the margin (20px on each side = 40px total)
            const margin = 20;
            const totalMargin = margin * 2;
            
            // Calculate zoom to fit with some padding
            const padding = 20;
            const availableWidth = viewportWidth - padding * 2;
            const availableHeight = viewportHeight - padding * 2;
            
            const zoomX = availableWidth / (svgWidth + totalMargin);
            const zoomY = availableHeight / (svgHeight + totalMargin);
            const newZoom = Math.min(zoomX, zoomY);
            
            // Clamp to zoom limits
            this.zoomFactor = Math.max(0.35, Math.min(2.0, newZoom));
            
            // Wait for Vue to update the size, then center
            this.$nextTick(() => {
                // The scrollable content size is now svgWidth * zoom + margins
                const scaledWidth = svgWidth * this.zoomFactor + totalMargin;
                const scaledHeight = svgHeight * this.zoomFactor + totalMargin;
                
                container.scrollLeft = Math.max(0, (scaledWidth - viewportWidth) / 2);
                container.scrollTop = Math.max(0, (scaledHeight - viewportHeight) / 2);
                
                // Emit status
                this.$emit('statusChange', { 
                    text: `Zoom: ${(this.zoomFactor * 100).toFixed(0)}%`, 
                    level: 'info' 
                });
            });
        }
    }
};

export { GraphvizViewerComponent };
