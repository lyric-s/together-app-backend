#!/usr/bin/env python3
"""OWASP ZAP automated security scanner for the Together API.

This script performs automated security scanning using OWASP ZAP, including:
- Spider scan to discover all API endpoints
- Active scan to detect vulnerabilities
- Report generation in HTML and JSON formats

Prerequisites:
    - OWASP ZAP running (via Docker or locally)
    - API server running and accessible

Usage:
    # Start ZAP via Docker first:
    docker-compose up -d zap

    # Run the scan:
    uv run python tests/security/zap_scan.py --target http://127.0.0.1:8000

    # With API key:
    uv run python tests/security/zap_scan.py \\
        --target http://127.0.0.1:8000 \\
        --api-key your-api-key

References:
    https://www.zaproxy.org/docs/api/
    https://www.zaproxy.org/docs/docker/api-scan/
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from zapv2 import ZAPv2


class ZAPScanner:
    """OWASP ZAP scanner wrapper for API security testing."""

    def __init__(
        self,
        zap_url: str = "http://127.0.0.1:8080",
        api_key: Optional[str] = None,
    ):
        """Initialize ZAP scanner.

        Args:
            zap_url: URL where ZAP is running (default: http://127.0.0.1:8080)
            api_key: ZAP API key (None if API key is disabled in ZAP)
        """
        proxies = {"http": zap_url, "https": zap_url}
        self.zap = ZAPv2(apikey=api_key, proxies=proxies)
        self.zap_url = zap_url
        print(f"✓ Connected to ZAP at {zap_url}")

    def spider_scan(self, target_url: str) -> str:
        """Run spider scan to discover endpoints.

        Args:
            target_url: Base URL to spider

        Returns:
            Spider scan ID
        """
        print(f"\n[1/3] Starting spider scan on {target_url}...")
        scan_id = self.zap.spider.scan(target_url)
        print(f"✓ Spider scan started (ID: {scan_id})")

        # Wait for spider to complete
        while int(self.zap.spider.status(scan_id)) < 100:
            progress = int(self.zap.spider.status(scan_id))
            print(f"  Spider progress: {progress}%", end="\r")
            time.sleep(2)

        print("  Spider progress: 100%")
        print("✓ Spider scan completed")

        # Show discovered URLs
        results = self.zap.spider.results(scan_id)
        print(f"  Discovered {len(results)} URLs")

        return scan_id

    def active_scan(self, target_url: str) -> str:
        """Run active security scan.

        Args:
            target_url: Base URL to scan

        Returns:
            Active scan ID
        """
        print(f"\n[2/3] Starting active security scan on {target_url}...")
        scan_id = self.zap.ascan.scan(target_url)
        print(f"✓ Active scan started (ID: {scan_id})")

        # Wait for scan to complete
        while int(self.zap.ascan.status(scan_id)) < 100:
            progress = int(self.zap.ascan.status(scan_id))
            print(f"  Scan progress: {progress}%", end="\r")
            time.sleep(5)

        print("  Scan progress: 100%")

        # Wait for passive scan to complete
        print("  Waiting for passive scan to complete...")
        while int(self.zap.pscan.records_to_scan) > 0:
            remaining = int(self.zap.pscan.records_to_scan)
            print(f"  Passive scan records remaining: {remaining}", end="\r")
            time.sleep(2)

        print("  Passive scan records remaining: 0")
        print("✓ Active scan completed")

        return scan_id

    def get_alerts(self, target_url: str) -> list:
        """Retrieve all security alerts found.

        Args:
            target_url: Base URL to get alerts for

        Returns:
            List of alert dictionaries
        """
        print("\n[3/3] Retrieving security alerts...")
        alerts = self.zap.alert.alerts(baseurl=target_url, start=0, count=5000)
        print(f"✓ Found {len(alerts)} security alerts")
        return alerts

    def print_alert_summary(self, alerts: list):
        """Print summary of security alerts by risk level.

        Args:
            alerts: List of alert dictionaries
        """
        # Count alerts by risk level
        risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
        for alert in alerts:
            risk = alert.get("risk", "Informational")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

        print("\n" + "=" * 60)
        print("SECURITY ALERT SUMMARY")
        print("=" * 60)
        print(f"  🔴 High:          {risk_counts['High']}")
        print(f"  🟠 Medium:        {risk_counts['Medium']}")
        print(f"  🟡 Low:           {risk_counts['Low']}")
        print(f"  🔵 Informational: {risk_counts['Informational']}")
        print("=" * 60)

        # Print high and medium risk alerts
        if risk_counts["High"] > 0 or risk_counts["Medium"] > 0:
            print("\nCRITICAL AND HIGH RISK ALERTS:")
            print("-" * 60)
            for alert in alerts:
                if alert.get("risk") in ["High", "Medium"]:
                    print(f"\n[{alert['risk']}] {alert['alert']}")
                    print(f"  URL: {alert['url']}")
                    print(f"  Description: {alert.get('description', '')[:100]}...")
                    if alert.get("solution"):
                        print(f"  Solution: {alert['solution'][:100]}...")

    def generate_reports(self, output_dir: Path):
        """Generate HTML and JSON reports.

        Args:
            output_dir: Directory to save reports
        """
        print("\nGenerating reports...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # HTML report
        html_path = output_dir / "zap_report.html"
        html_report = self.zap.core.htmlreport()
        html_path.write_text(html_report)
        print(f"✓ HTML report saved to: {html_path}")

        # XML report
        xml_path = output_dir / "zap_report.xml"
        xml_report = self.zap.core.xmlreport()
        xml_path.write_text(xml_report)
        print(f"✓ XML report saved to: {xml_path}")


def main():
    """Main entry point for ZAP scanner."""
    parser = argparse.ArgumentParser(
        description="Run OWASP ZAP security scan on Together API"
    )
    parser.add_argument(
        "--target",
        default="http://127.0.0.1:8000",
        help="Target API URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--zap-url",
        default="http://127.0.0.1:8080",
        help="ZAP proxy URL (default: http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--api-key",
        help="ZAP API key (None if disabled)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/security/reports"),
        help="Output directory for reports (default: tests/security/reports)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("OWASP ZAP SECURITY SCANNER")
    print("=" * 60)

    try:
        # Initialize scanner
        scanner = ZAPScanner(zap_url=args.zap_url, api_key=args.api_key)

        # Run spider scan
        scanner.spider_scan(args.target)

        # Run active scan
        scanner.active_scan(args.target)

        # Get and display alerts
        alerts = scanner.get_alerts(args.target)
        scanner.print_alert_summary(alerts)

        # Generate reports
        scanner.generate_reports(args.output)

        print("\n" + "=" * 60)
        print("SCAN COMPLETED SUCCESSFULLY")
        print("=" * 60)

        # Exit with error code if high/medium risks found
        high_risk = sum(1 for a in alerts if a.get("risk") == "High")
        medium_risk = sum(1 for a in alerts if a.get("risk") == "Medium")

        if high_risk > 0:
            print(f"\n⚠️  WARNING: {high_risk} HIGH RISK vulnerabilities found!")
            sys.exit(1)
        elif medium_risk > 0:
            print(f"\n⚠️  WARNING: {medium_risk} MEDIUM RISK vulnerabilities found!")
            sys.exit(1)
        else:
            print("\n✅ No high or medium risk vulnerabilities found.")
            sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error during scan: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
