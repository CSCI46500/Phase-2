# Package Metrics GUI

A simple graphical interface for analyzing package metrics.

## Features

- 🎨 Clean, easy-to-use interface
- 📊 Real-time analysis of packages
- 📋 Results displayed in readable format
- 💾 JSON output included
- 📸 Screenshot-friendly design

## How to Run

### Option 1: Using the launcher script
```bash
./run_gui.sh
```

### Option 2: Direct Python execution
```bash
python3 gui.py
```

### Option 3: Make it executable
```bash
chmod +x gui.py
./gui.py
```

## How to Use

1. **Launch the GUI** using one of the methods above
2. **Enter URLs** in the input fields:
   - Code URL (GitHub repository)
   - Dataset URL (HuggingFace dataset)
   - Model URL (HuggingFace model)
3. **Click "Analyze Package"** to start the analysis
4. **Wait** for results to appear (may take 30-60 seconds)
5. **View results** in the scrollable text area

## Quick Test

Click the **"Load Example"** button to automatically fill in sample URLs:
- Code: https://github.com/huggingface/transformers
- Dataset: https://huggingface.co/datasets/squad
- Model: https://huggingface.co/bert-base-uncased

Then click **"Analyze Package"** to see it work!

## GUI Components

### Input Section
- **Code URL**: GitHub repository URL
- **Dataset URL**: HuggingFace dataset URL
- **Model URL**: HuggingFace model URL

### Buttons
- **Analyze Package**: Runs the analysis
- **Clear All**: Clears all inputs and results
- **Load Example**: Fills in example URLs for testing

### Results Section
Shows:
- Package name and category
- All metric scores (0.0 to 1.0)
- Raw JSON output
- Status messages

## Taking Screenshots

### For Assignment Submission:

1. **Before Analysis Screenshot:**
   - Fill in URLs (or use "Load Example")
   - Take screenshot showing the input fields filled

2. **During Analysis Screenshot:**
   - Click "Analyze Package"
   - Take screenshot showing "Analyzing package..." status

3. **After Analysis Screenshot:**
   - Wait for analysis to complete
   - Take screenshot showing the results
   - Make sure to capture:
     - The input URLs at the top
     - The metrics scores
     - The "Analysis complete" message

### Screenshot Tips:
- Make sure the window is fully visible
- Use full window size (resize if needed)
- Capture the entire application window
- Results are scrollable - you can show different sections

## Example URLs to Test

### Example 1: BERT Model
```
Code URL: https://github.com/huggingface/transformers
Dataset URL: https://huggingface.co/datasets/squad
Model URL: https://huggingface.co/bert-base-uncased
```

### Example 2: GPT-2 Model
```
Code URL: https://github.com/openai/gpt-2
Dataset URL: https://huggingface.co/datasets/wikitext
Model URL: https://huggingface.co/gpt2
```

### Example 3: Just a Model
```
Code URL: (leave empty)
Dataset URL: (leave empty)
Model URL: https://huggingface.co/distilbert-base-uncased
```

## Troubleshooting

### GUI doesn't open
```bash
# Check if tkinter is installed
python3 -c "import tkinter; print('Tkinter OK')"

# If not, install it (macOS)
brew install python-tk

# Or on Linux
sudo apt-get install python3-tk
```

### "Module not found" error
```bash
# Install dependencies
./run install
# or
pip install -r dependencies.txt
```

### Analysis takes too long
- This is normal for the first run
- HuggingFace API calls can take 30-60 seconds
- Be patient, results will appear

### Window too small
- Resize the window by dragging corners
- Scroll in the results area to see all output

## What the GUI Shows

### Metrics Displayed:
1. **Net Score** - Overall package quality (0-1)
2. **Ramp-Up Time** - How easy to get started (0-1)
3. **Bus Factor** - Team diversity (0-1)
4. **Performance Claims** - Has benchmarks (0-1)
5. **License** - Has valid license (0-1)
6. **Dataset Quality** - Dataset documentation/usage (0-1)
7. **Code Quality** - Code repository quality (0-1)
8. **Dataset and Code Score** - Both present (0-1)
9. **Size Scores** - Individual size metrics

### JSON Output:
Full raw JSON output is included at the bottom for:
- API integrations
- Debugging
- Detailed analysis

## System Requirements

- Python 3.10 or higher
- tkinter (included with most Python installations)
- Internet connection (for API calls)
- Required packages from dependencies.txt

## Performance Notes

- First analysis may take 30-60 seconds
- GUI remains responsive during analysis
- Progress bar shows activity
- Results appear when complete

## For Cloud Deployment Screenshot

If you want to show the cloud-deployed version:

1. Deploy to AWS (using the CD pipeline)
2. SSH into the EC2 instance or use AWS CloudShell
3. Run the GUI there (if X11 forwarding is set up)

**OR** create a REST API endpoint that you can call from your local GUI:
- The GUI can be modified to call your deployed API
- This shows local → cloud interaction
- Good for screenshots showing cloud service

## Need Help?

- Check that all URLs are valid
- Try the "Load Example" button first
- Look at the status messages at the top
- Check terminal for any error messages

---

**Ready to go!** Launch the GUI and start analyzing packages! 🚀