// DNA Decrypt - Windows launcher.
// The whole app (DNA-Health-Report.html) is embedded in this .exe. On launch it is copied to
// %LOCALAPPDATA%\DNADecrypt\app and opened in a standalone Edge (or Chrome) app window
// with its own private profile, extensions off, and all network traffic blocked.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("DNA Decrypt")]
[assembly: AssemblyProduct("DNA Decrypt")]
[assembly: AssemblyCompany("DNA Decrypt")]
[assembly: AssemblyCopyright("Copyright (c) 2026 DNA Decrypt")]
[assembly: AssemblyVersion("0.1.5.0")]
[assembly: AssemblyFileVersion("0.1.5.0")]

static class Launcher
{
    const string AppTitle = "DNA Decrypt";
    const string ResourceName = "DNA-Health-Report.html";

    [STAThread]
    static int Main()
    {
        try
        {
            string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DNADecrypt");
            string appDir = Path.Combine(root, "app");
            string profileDir = Path.Combine(root, "browser-profile");
            Directory.CreateDirectory(appDir);
            Directory.CreateDirectory(profileDir);

            string htmlPath = Path.Combine(appDir, ResourceName);
            WriteEmbeddedHtml(htmlPath);
            string url = new Uri(htmlPath).AbsoluteUri;

            string browser = FindBrowser();
            if (browser == null)
            {
                MessageBox.Show("Microsoft Edge or Google Chrome was not found, so the report will open in your default browser instead.",
                    AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Information);
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
                return 0;
            }

            string args = string.Join(" ", new[] {
                "--app=\"" + url + "\"",
                "--user-data-dir=\"" + profileDir + "\"",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-sync",
                "--disable-features=Translate,msEdgeShopping,msEdgeCollections",
                // Privacy: send every network request to a dead proxy so nothing can leave the computer.
                "--proxy-server=\"127.0.0.1:9\"",
                "--proxy-bypass-list=\"<-loopback>\"",
                "--window-size=1150,900"
            });
            Process.Start(new ProcessStartInfo(browser, args) { UseShellExecute = false });
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show("The program could not start:\n\n" + ex.Message, AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    static void WriteEmbeddedHtml(string path)
    {
        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(ResourceName))
        {
            if (s == null) throw new InvalidOperationException("The embedded report program is missing from this file.");
            byte[] data = new byte[s.Length];
            int read = 0;
            while (read < data.Length)
            {
                int n = s.Read(data, read, data.Length - read);
                if (n <= 0) throw new EndOfStreamException("The embedded report program is incomplete.");
                read += n;
            }
            if (File.Exists(path))
            {
                byte[] old = File.ReadAllBytes(path);
                if (old.Length == data.Length && SameBytes(old, data)) return;
            }
            File.WriteAllBytes(path, data);
        }
    }

    static bool SameBytes(byte[] a, byte[] b)
    {
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    static string FindBrowser()
    {
        string pf86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)") ?? "";
        string pf = Environment.GetEnvironmentVariable("ProgramFiles") ?? "";
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] candidates = {
            Path.Combine(pf86, @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(pf, @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(pf, @"Google\Chrome\Application\chrome.exe"),
            Path.Combine(pf86, @"Google\Chrome\Application\chrome.exe"),
            Path.Combine(local, @"Google\Chrome\Application\chrome.exe")
        };
        foreach (string c in candidates) if (c.Length > 0 && File.Exists(c)) return c;
        return null;
    }
}
