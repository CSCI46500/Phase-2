#!/usr/bin/env python3
"""
Simple GUI for Package Metrics System
Allows users to input package URLs and view metrics results
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import threading
from metrics import Metrics


class PackageMetricsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Package Metrics Analyzer")
        self.root.geometry("900x700")

        # Configure style - use aqua theme for macOS
        style = ttk.Style()
        try:
            style.theme_use('aqua')
        except:
            style.theme_use('default')

        # Main container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Package Metrics Analyzer",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Package URLs", padding="10")
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # Code URL
        ttk.Label(input_frame, text="Code URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.code_url = ttk.Entry(input_frame, width=60)
        self.code_url.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        # Dataset URL
        ttk.Label(input_frame, text="Dataset URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.dataset_url = ttk.Entry(input_frame, width=60)
        self.dataset_url.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        # Model URL
        ttk.Label(input_frame, text="Model URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.model_url = ttk.Entry(input_frame, width=60)
        self.model_url.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)

        # Buttons Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        # Analyze Button
        self.analyze_btn = ttk.Button(button_frame, text="Analyze Package",
                                      command=self.analyze_package)
        self.analyze_btn.grid(row=0, column=0, padx=5)

        # Clear Button
        clear_btn = ttk.Button(button_frame, text="Clear All",
                              command=self.clear_all)
        clear_btn.grid(row=0, column=1, padx=5)

        # Load Example Button
        example_btn = ttk.Button(button_frame, text="Load Example",
                                command=self.load_example)
        example_btn.grid(row=0, column=2, padx=5)

        # Status Label
        self.status_label = ttk.Label(main_frame, text="Ready",
                                     font=("Arial", 10))
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Results Section
        results_frame = ttk.LabelFrame(main_frame, text="Analysis Results", padding="10")
        results_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # Results Text Area
        self.results_text = scrolledtext.ScrolledText(results_frame, height=20, width=80,
                                                      font=("Courier", 10))
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure main frame row weights
        main_frame.rowconfigure(5, weight=1)

        # Force update on macOS
        self.root.update_idletasks()

    def load_example(self):
        """Load example URLs"""
        self.code_url.delete(0, tk.END)
        self.dataset_url.delete(0, tk.END)
        self.model_url.delete(0, tk.END)

        self.code_url.insert(0, "https://github.com/huggingface/transformers")
        self.dataset_url.insert(0, "https://huggingface.co/datasets/squad")
        self.model_url.insert(0, "https://huggingface.co/bert-base-uncased")

        self.status_label.config(text="Example URLs loaded")

    def clear_all(self):
        """Clear all inputs and results"""
        self.code_url.delete(0, tk.END)
        self.dataset_url.delete(0, tk.END)
        self.model_url.delete(0, tk.END)
        self.results_text.delete(1.0, tk.END)
        self.status_label.config(text="Cleared")

    def analyze_package(self):
        """Analyze the package with given URLs"""
        code = self.code_url.get().strip()
        dataset = self.dataset_url.get().strip()
        model = self.model_url.get().strip()

        if not code and not dataset and not model:
            messagebox.showwarning("Input Required",
                                  "Please enter at least one URL")
            return

        # Disable button during processing
        self.analyze_btn.config(state='disabled')
        self.status_label.config(text="Analyzing package... This may take a moment")
        self.progress.start(10)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Processing request...\n")
        self.results_text.insert(tk.END, f"Code URL: {code if code else 'N/A'}\n")
        self.results_text.insert(tk.END, f"Dataset URL: {dataset if dataset else 'N/A'}\n")
        self.results_text.insert(tk.END, f"Model URL: {model if model else 'N/A'}\n")
        self.results_text.insert(tk.END, "\n" + "="*80 + "\n\n")

        # Run analysis in separate thread to prevent GUI freezing
        thread = threading.Thread(target=self._run_analysis,
                                 args=(code, dataset, model))
        thread.daemon = True
        thread.start()

    def _run_analysis(self, code_url, dataset_url, model_url):
        """Run analysis in background thread"""
        try:
            # Create input dict
            input_dict = {
                "code_url": code_url if code_url else "",
                "dataset_url": dataset_url if dataset_url else "",
                "model_url": model_url if model_url else ""
            }

            # Run metrics
            metrics = Metrics(input_dict)
            result = metrics.run()

            # Format and display results
            self._display_results(result)

        except Exception as e:
            self._display_error(str(e))
        finally:
            # Re-enable button
            self.root.after(0, self._analysis_complete)

    def _display_results(self, result):
        """Display results in the text area"""
        def update_ui():
            self.results_text.insert(tk.END, "ANALYSIS RESULTS\n")
            self.results_text.insert(tk.END, "="*80 + "\n\n")

            # Package Info
            self.results_text.insert(tk.END, f"Package Name: {result.get('name', 'N/A')}\n")
            self.results_text.insert(tk.END, f"Category: {result.get('category', 'N/A')}\n\n")

            # Metrics
            self.results_text.insert(tk.END, "METRICS:\n")
            self.results_text.insert(tk.END, "-"*80 + "\n")

            metrics_to_display = [
                ("Net Score", "net_score"),
                ("Ramp-Up Time", "ramp_up_time"),
                ("Bus Factor", "bus_factor"),
                ("Performance Claims", "performance_claims"),
                ("License", "license"),
                ("Dataset Quality", "dataset_quality"),
                ("Code Quality", "code_quality"),
                ("Dataset and Code Score", "dataset_and_code_score"),
            ]

            for name, key in metrics_to_display:
                value = result.get(key, "N/A")
                if isinstance(value, (int, float)):
                    self.results_text.insert(tk.END, f"  {name:.<30} {value:.3f}\n")
                else:
                    self.results_text.insert(tk.END, f"  {name:.<30} {value}\n")

            # Size Score (if it's a dict)
            if "size_score" in result and isinstance(result["size_score"], dict):
                self.results_text.insert(tk.END, "\n  Size Scores:\n")
                for category, score in result["size_score"].items():
                    if isinstance(score, (int, float)):
                        self.results_text.insert(tk.END, f"    {category:.<28} {score:.3f}\n")

            # Raw JSON
            self.results_text.insert(tk.END, "\n" + "="*80 + "\n")
            self.results_text.insert(tk.END, "RAW JSON OUTPUT:\n")
            self.results_text.insert(tk.END, "-"*80 + "\n")
            self.results_text.insert(tk.END, json.dumps(result, indent=2, ensure_ascii=False))
            self.results_text.insert(tk.END, "\n\n✅ Analysis complete!")

            self.status_label.config(text="✅ Analysis completed successfully")

        self.root.after(0, update_ui)

    def _display_error(self, error_msg):
        """Display error message"""
        def update_ui():
            self.results_text.insert(tk.END, "\n❌ ERROR:\n")
            self.results_text.insert(tk.END, "="*80 + "\n")
            self.results_text.insert(tk.END, f"{error_msg}\n")
            self.status_label.config(text="❌ Analysis failed")

        self.root.after(0, update_ui)

    def _analysis_complete(self):
        """Re-enable UI after analysis"""
        self.progress.stop()
        self.analyze_btn.config(state='normal')


def main():
    root = tk.Tk()
    app = PackageMetricsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
