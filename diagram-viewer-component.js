/**
 * Reusable diagram viewer component for documentation
 * Wraps GraphvizViewerComponent with loading state and auto-fit behavior
 */
import { GraphvizViewerComponent } from './graphviz-viewer.js';

const DiagramViewerComponent = {
    components: {
        'graphviz-viewer': GraphvizViewerComponent
    },
    props: {
        dotSource: {
            type: String,
            default: null
        },
        isLoading: {
            type: Boolean,
            default: false
        }
    },
    template: `
        <div class="diagram-viewer">
            <div v-if="isLoading" class="example-loading">
                <p>⏳ Generating diagram...</p>
            </div>
            <graphviz-viewer
                v-else
                ref="viewer"
                :dot-source="dotSource"
                placeholder="Diagram will appear here"
            />
        </div>
    `,
    watch: {
        async dotSource(newVal) {
            if (newVal) {
                // Wait for viewer to render, then zoom to fit
                await this.$nextTick();
                await new Promise(resolve => setTimeout(resolve, 2000));
                if (this.$refs.viewer) {
                    this.$refs.viewer.zoomToFit();
                }
            }
        }
    },
    async mounted() {
        if (this.dotSource) {
            // Wait for viewer to render, then zoom to fit
            await this.$nextTick();
            await new Promise(resolve => setTimeout(resolve, 2000));
            if (this.$refs.viewer) {
                this.$refs.viewer.zoomToFit();
            }
        }
    }
};

export { DiagramViewerComponent };

