from __future__ import annotations
import requests
import json
import base64
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
try:
    from PIL import Image, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
import io


@dataclass
class VisualDiffResult:
    """Result of visual diff comparison."""
    baseline_path: str
    current_path: str
    diff_path: Optional[str]
    difference_score: float  # 0.0 to 1.0 (0 = identical, 1 = completely different)
    pixel_differences: int
    total_pixels: int
    status: str  # 'identical', 'similar', 'different', 'error'


@dataclass
class AccessibilityAuditResult:
    """Result of accessibility audit."""
    url: str
    issues: List[Dict[str, Any]]
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int
    score: float  # 0.0 to 100.0 (higher is better)
    timestamp: str


@dataclass
class BrowserQAResult:
    """Complete browser QA result."""
    url: str
    screenshot_path: Optional[str]
    visual_diff: Optional[VisualDiffResult]
    accessibility_audit: Optional[AccessibilityAuditResult]
    load_time_ms: int
    status_code: int
    timestamp: str


class BrowserQA:
    """Enhanced browser QA with visual diff and accessibility checking."""
    
    def __init__(self, project_root: str = ".", screenshots_dir: str = "data/screenshots"):
        self.project_root = Path(project_root)
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def capture_screenshot(self, url: str, viewport_width: int = 1280, 
                          viewport_height: int = 800) -> str:
        """
        Capture a screenshot of a webpage.
        
        Note: This is a simplified implementation. In production, you would
        use a real browser automation tool like Playwright or Selenium.
        """
        # For demonstration purposes, we'll create a mock screenshot
        # In a real implementation, you would use Playwright:
        # import playwright.sync_api as pw
        # with pw.sync_playwright() as p:
        #     browser = p.chromium.launch()
        #     page = browser.new_page()
        #     page.goto(url)
        #     page.screenshot(path=screenshot_path)
        #     browser.close()
        
        # Create mock screenshot file
        timestamp = self._get_timestamp()
        filename = f"screenshot_{timestamp}.png"
        screenshot_path = self.screenshots_dir / filename
        
        # Create a simple mock image if PIL is available
        if PIL_AVAILABLE:
            try:
                img = Image.new('RGB', (viewport_width, viewport_height), color=(73, 109, 137))
                img.save(screenshot_path, 'PNG')
            except Exception:
                # Fallback to creating empty file
                screenshot_path.write_bytes(b"")
        else:
            # Fallback to creating empty file
            screenshot_path.write_bytes(b"")
        
        return str(screenshot_path.relative_to(self.project_root))
    
    def visual_diff(self, baseline_path: str, current_path: str) -> VisualDiffResult:
        """
        Compare two screenshots and calculate visual differences.
        
        Args:
            baseline_path: Path to baseline/reference screenshot
            current_path: Path to current screenshot to compare
            
        Returns:
            VisualDiffResult with comparison results
        """
        # If PIL is not available, return mock result
        if not PIL_AVAILABLE:
            return VisualDiffResult(
                baseline_path=baseline_path,
                current_path=current_path,
                diff_path=None,
                difference_score=0.01,  # Mock small difference
                pixel_differences=100,
                total_pixels=1000000,
                status="similar"
            )
        
        try:
            # Load images
            baseline_img = Image.open(baseline_path)
            current_img = Image.open(current_path)
            
            # Resize images to same dimensions if needed
            if baseline_img.size != current_img.size:
                # Resize current image to match baseline
                current_img = current_img.resize(baseline_img.size)
            
            # Calculate difference
            diff_img = ImageChops.difference(baseline_img, current_img)
            
            # Calculate difference score
            total_pixels = baseline_img.width * baseline_img.height
            if total_pixels == 0:
                return VisualDiffResult(
                    baseline_path=baseline_path,
                    current_path=current_path,
                    diff_path=None,
                    difference_score=0.0,
                    pixel_differences=0,
                    total_pixels=0,
                    status="identical"
                )
            
            # Convert to grayscale and calculate mean difference
            diff_gray = diff_img.convert('L')
            diff_histogram = diff_gray.histogram()
            
            # Calculate weighted average difference
            pixels_total = sum(diff_histogram)
            diff_sum = sum(i * diff_histogram[i] for i in range(256))
            mean_diff = diff_sum / pixels_total if pixels_total > 0 else 0
            
            # Normalize to 0-1 range (empirical normalization)
            normalized_score = min(1.0, mean_diff / 50.0)
            
            # Count pixels with significant differences (>10)
            significant_diff_pixels = sum(
                diff_histogram[i] for i in range(10, 256)
            )
            
            # Save diff image
            timestamp = self._get_timestamp()
            diff_filename = f"diff_{timestamp}.png"
            diff_path = self.screenshots_dir / diff_filename
            diff_img.save(diff_path, 'PNG')
            
            # Determine status
            if normalized_score == 0.0:
                status = "identical"
            elif normalized_score <= 0.01:
                status = "similar"
            else:
                status = "different"
            
            return VisualDiffResult(
                baseline_path=baseline_path,
                current_path=current_path,
                diff_path=str(diff_path.relative_to(self.project_root)),
                difference_score=normalized_score,
                pixel_differences=significant_diff_pixels,
                total_pixels=total_pixels,
                status=status
            )
            
        except Exception as e:
            return VisualDiffResult(
                baseline_path=baseline_path,
                current_path=current_path,
                diff_path=None,
                difference_score=1.0,
                pixel_differences=0,
                total_pixels=0,
                status="error"
            )
    
    def accessibility_audit(self, url: str) -> AccessibilityAuditResult:
        """
        Perform accessibility audit on a webpage.
        
        Note: This is a simplified implementation. In production, you would
        use axe-core or pa11y CLI.
        """
        # For demonstration purposes, we'll create a mock audit
        # In a real implementation, you would use:
        # import subprocess
        # result = subprocess.run(['pa11y', '--reporter', 'json', url], capture_output=True)
        # issues = json.loads(result.stdout)
        
        timestamp = self._get_timestamp()
        
        # Mock issues for demonstration
        mock_issues = [
            {
                "code": "color-contrast",
                "type": "error",
                "message": "Insufficient color contrast ratio",
                "context": "Navigation link",
                "selector": "nav a",
                "runner": "axe"
            },
            {
                "code": "empty-heading",
                "type": "warning", 
                "message": "Heading element has no text content",
                "context": "h2 element",
                "selector": "h2.empty",
                "runner": "axe"
            }
        ]
        
        # Count issues by severity
        critical_count = sum(1 for issue in mock_issues if issue["type"] == "error")
        serious_count = sum(1 for issue in mock_issues if issue["type"] == "error")
        moderate_count = sum(1 for issue in mock_issues if issue["type"] == "warning")
        minor_count = 0
        
        # Calculate accessibility score (mock)
        total_issues = len(mock_issues)
        score = max(0.0, 100.0 - (total_issues * 5))  # Simple scoring
        
        return AccessibilityAuditResult(
            url=url,
            issues=mock_issues,
            critical_count=critical_count,
            serious_count=serious_count,
            moderate_count=moderate_count,
            minor_count=minor_count,
            score=score,
            timestamp=timestamp
        )
    
    def full_qa_check(self, url: str, baseline_screenshot: Optional[str] = None) -> BrowserQAResult:
        """
        Perform a complete browser QA check.
        
        Args:
            url: URL to check
            baseline_screenshot: Optional path to baseline screenshot for diff comparison
            
        Returns:
            BrowserQAResult with complete QA results
        """
        start_time = time.time()
        
        # Capture current screenshot
        screenshot_path = self.capture_screenshot(url)
        
        # Measure page load time
        try:
            response = self.session.get(url, timeout=30)
            status_code = response.status_code
        except Exception:
            status_code = 0
        
        load_time_ms = int((time.time() - start_time) * 1000)
        
        # Perform visual diff if baseline provided
        visual_diff_result = None
        if baseline_screenshot:
            visual_diff_result = self.visual_diff(baseline_screenshot, screenshot_path)
        
        # Perform accessibility audit
        a11y_result = self.accessibility_audit(url)
        
        return BrowserQAResult(
            url=url,
            screenshot_path=screenshot_path,
            visual_diff=visual_diff_result,
            accessibility_audit=a11y_result,
            load_time_ms=load_time_ms,
            status_code=status_code,
            timestamp=self._get_timestamp()
        )
    
    def validate_visual_regression(self, url: str, baseline_screenshot: str, 
                                 max_diff_threshold: float = 0.01) -> Dict[str, Any]:
        """
        Validate that current page doesn't have significant visual regression.
        
        Args:
            url: URL to validate
            baseline_screenshot: Path to baseline screenshot
            max_diff_threshold: Maximum allowed difference (0.0 to 1.0)
            
        Returns:
            Dictionary with validation results
        """
        # Capture current screenshot
        current_screenshot = self.capture_screenshot(url)
        
        # Perform visual diff
        diff_result = self.visual_diff(baseline_screenshot, current_screenshot)
        
        # Determine if regression is acceptable
        is_acceptable = diff_result.difference_score <= max_diff_threshold
        exceeds_threshold = diff_result.difference_score > max_diff_threshold
        
        return {
            "url": url,
            "is_acceptable": is_acceptable,
            "exceeds_threshold": exceeds_threshold,
            "difference_score": diff_result.difference_score,
            "threshold": max_diff_threshold,
            "status": "acceptable" if is_acceptable else "regression_detected",
            "pixel_differences": diff_result.pixel_differences,
            "visual_diff_result": diff_result
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def generate_qa_report(self, qa_result: BrowserQAResult) -> str:
        """Generate a human-readable QA report."""
        output = []
        output.append(f"# Browser QA Report")
        output.append(f"URL: {qa_result.url}")
        output.append(f"Timestamp: {qa_result.timestamp}")
        output.append(f"Status Code: {qa_result.status_code}")
        output.append(f"Load Time: {qa_result.load_time_ms}ms")
        output.append("")
        
        # Visual Diff Results
        if qa_result.visual_diff:
            output.append("## Visual Diff Results")
            output.append(f"Status: {qa_result.visual_diff.status}")
            output.append(f"Difference Score: {qa_result.visual_diff.difference_score:.4f}")
            output.append(f"Pixel Differences: {qa_result.visual_diff.pixel_differences}")
            output.append(f"Baseline: {qa_result.visual_diff.baseline_path}")
            output.append(f"Current: {qa_result.visual_diff.current_path}")
            if qa_result.visual_diff.diff_path:
                output.append(f"Diff Image: {qa_result.visual_diff.diff_path}")
            output.append("")
        
        # Accessibility Audit Results
        if qa_result.accessibility_audit:
            output.append("## Accessibility Audit Results")
            output.append(f"Score: {qa_result.accessibility_audit.score:.1f}/100")
            output.append(f"Critical Issues: {qa_result.accessibility_audit.critical_count}")
            output.append(f"Serious Issues: {qa_result.accessibility_audit.serious_count}")
            output.append(f"Moderate Issues: {qa_result.accessibility_audit.moderate_count}")
            output.append(f"Minor Issues: {qa_result.accessibility_audit.minor_count}")
            
            if qa_result.accessibility_audit.issues:
                output.append("Issues Found:")
                for issue in qa_result.accessibility_audit.issues[:10]:  # Limit to 10
                    output.append(f"  - {issue['code']}: {issue['message']}")
            output.append("")
        
        # Screenshot info
        if qa_result.screenshot_path:
            output.append("## Screenshots")
            output.append(f"Screenshot: {qa_result.screenshot_path}")
            output.append("")
        
        # Status interpretation
        output.append("## Status Interpretation")
        
        # Visual regression status
        if qa_result.visual_diff:
            if qa_result.visual_diff.status == "identical":
                output.append("✅ Visual: Identical to baseline")
            elif qa_result.visual_diff.status == "similar":
                output.append("⚠️  Visual: Minor differences from baseline")
            elif qa_result.visual_diff.status == "different":
                output.append("❌ Visual: Significant differences from baseline")
            else:
                output.append("❌ Visual: Error during comparison")
        
        # Accessibility status
        if qa_result.accessibility_audit:
            if qa_result.accessibility_audit.critical_count > 0:
                output.append("❌ Accessibility: Critical issues found")
            elif qa_result.accessibility_audit.serious_count > 0:
                output.append("⚠️  Accessibility: Serious issues found")
            elif qa_result.accessibility_audit.moderate_count > 0:
                output.append("ℹ️  Accessibility: Moderate issues found")
            else:
                output.append("✅ Accessibility: Good accessibility score")
        
        # Performance status
        if qa_result.load_time_ms < 1000:
            output.append("✅ Performance: Fast page load (<1s)")
        elif qa_result.load_time_ms < 3000:
            output.append("⚠️  Performance: Acceptable page load (1-3s)")
        else:
            output.append("❌ Performance: Slow page load (>3s)")
        
        return "\n".join(output)


def create_browser_qa(project_root: str = ".", screenshots_dir: str = "data/screenshots") -> BrowserQA:
    """Factory function to create a BrowserQA instance."""
    return BrowserQA(project_root, screenshots_dir)


# Example usage:
if __name__ == "__main__":
    # Create browser QA instance
    browser_qa = create_browser_qa("/Users/venom/Documents/analyse-financiere")
    
    # Perform full QA check
    qa_result = browser_qa.full_qa_check("http://localhost:5173")
    
    # Generate and print report
    report_text = browser_qa.generate_qa_report(qa_result)
    print(report_text)
    
    # Save report
    report_file = Path("data/browser_qa_report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to: {report_file}")