/**
 * GraphvizViewer - Reusable Vue mixin for interactive SVG graph viewing
 * Provides zoom and pan functionality for Graphviz-rendered graphs
 */
const GraphvizViewerMixin = {
    data() {
        return {
            zoomFactor: 1.0,
            isPanning: false,
            panStartX: 0,
            panStartY: 0,
            scrollStartX: 0,
            scrollStartY: 0
        };
    },
    methods: {
        /**
         * Render DOT string to SVG using @hpcc-js/wasm
         * @param {string} dotSource - Graphviz DOT source string
         * @param {string} containerRef - Name of the ref for the SVG container element
         */
        async renderGraphviz(dotSource, containerRef = 'svgContainer') {
            if (!dotSource) return;
            
            // Wait for next tick to ensure DOM is updated
            await this.$nextTick();
            
            const container = this.$refs[containerRef];
            if (!container) {
                console.warn(`Container ref "${containerRef}" not found`);
                return;
            }
            
            try {
                // Use @hpcc-js/wasm to render DOT to SVG
                const svg = await window['@hpcc-js/wasm'].graphviz.layout(
                    dotSource, 
                    'svg', 
                    'dot'
                );
                container.innerHTML = svg;
                
                // Notify status if available
                if (this.setStatus) {
                    this.setStatus(`Zoom: ${(this.zoomFactor * 100).toFixed(0)}%`, 'info');
                }
                
                return true;
            } catch (error) {
                console.error('Graphviz rendering error:', error);
                if (this.setStatus) {
                    this.setStatus('Graph rendering failed: ' + error.message, 'error');
                }
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
            
            // Adjust scroll position to keep mouse point stable
            const zoomRatio = this.zoomFactor / oldZoom;
            container.scrollLeft = scrollX * zoomRatio + (mouseX * (zoomRatio - 1));
            container.scrollTop = scrollY * zoomRatio + (mouseY * (zoomRatio - 1));
            
            // Update status if available
            if (this.setStatus) {
                this.setStatus(`Zoom: ${(this.zoomFactor * 100).toFixed(0)}%`, 'info');
            }
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
        }
    }
};

