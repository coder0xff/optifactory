/**
 * Reusable diagram viewer component for documentation
 */
import { GraphvizViewerMixin } from './graphviz-viewer.js';

const DiagramViewerComponent = {
    mixins: [GraphvizViewerMixin],
    props: {
        dotSource: {
            type: String,
            default: null
        },
        isLoading: {
            type: Boolean,
            default: false
        },
        containerRef: {
            type: String,
            required: true
        }
    },
    template: `
        <div class="diagram-viewer">
            <div v-if="isLoading" class="example-loading">
                <p>⏳ Generating diagram...</p>
            </div>
            <div v-else class="viewer-container" 
                 ref="viewerContainer"
                 @wheel="handleZoom"
                 @mousedown="startPan"
                 @mousemove="handlePan"
                 @mouseup="endPan"
                 @mouseleave="endPan">
                <div class="viewer-content">
                    <div class="viewer-svg" ref="svgContainer"></div>
                </div>
            </div>
            <div v-if="!isLoading && dotSource" class="zoom-indicator">
                Zoom: {{ (zoomFactor * 100).toFixed(0) }}%
                <button class="zoom-fit-button" @click="zoomToFit">Fit</button>
            </div>
        </div>
    `,
    watch: {
        async dotSource(newVal) {
            if (newVal) {
                await this.$nextTick();
                await this.renderDiagram();
            }
        }
    },
    mounted() {
        if (this.dotSource) {
            this.renderDiagram();
        }
    },
    methods: {
        async renderDiagram() {
            await this.$nextTick();
            const rendered = await this.renderGraphviz(this.dotSource, 'svgContainer');
            
            if (rendered) {
                // Wait for container to be properly sized before fitting
                // Use setTimeout to allow browser to complete layout
                await new Promise(resolve => setTimeout(resolve, 1000));
                this.zoomToFit();
            }
        }
    }
};

export { DiagramViewerComponent };

