using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;
using System.Reflection;

[assembly: AssemblyTitle("NeuroLytics")]
[assembly: AssemblyDescription("NeuroLytics ML and Data Intelligence Desktop Launcher")]
[assembly: AssemblyCompany("NeuroLytics")]
[assembly: AssemblyProduct("NeuroLytics")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

internal static class NeuroLyticsLauncher
{
    private const int Port = 5000;
    private const string Url = "http://127.0.0.1:5000/";

    [STAThread]
    private static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
        string python = Path.Combine(root, "venv", "Scripts", "python.exe");
        string script = Path.Combine(root, "scripts", "start_neurolytics.py");
        string logDir = Path.Combine(root, "logs");
        Directory.CreateDirectory(logDir);

        try
        {
            if (!PortOpen("127.0.0.1", Port))
            {
                if (!File.Exists(python))
                    throw new FileNotFoundException("NeuroLytics Python environment was not found.", python);
                if (!File.Exists(script))
                    throw new FileNotFoundException("NeuroLytics startup script was not found.", script);

                var psi = new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = "scripts\\start_neurolytics.py",
                    WorkingDirectory = root,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                psi.EnvironmentVariables["NEUROLYTICS_OPEN_BROWSER"] = "0";
                Process.Start(psi);
            }

            bool ready = false;
            for (int i = 0; i < 60; i++)
            {
                if (PortOpen("127.0.0.1", Port))
                {
                    ready = true;
                    break;
                }
                Thread.Sleep(500);
            }

            if (!ready)
                throw new Exception("NeuroLytics did not become ready on port 5000.");

            Process.Start(new ProcessStartInfo
            {
                FileName = Url,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            File.AppendAllText(
                Path.Combine(logDir, "desktop_launcher.log"),
                DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " ERROR " + ex + Environment.NewLine);
            MessageBox.Show(
                "NeuroLytics could not start.\r\n\r\n" + ex.Message +
                "\r\n\r\nYour existing database and model files were not modified.",
                "NeuroLytics",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }

    private static bool PortOpen(string host, int port)
    {
        try
        {
            using (var client = new TcpClient())
            {
                var result = client.BeginConnect(host, port, null, null);
                if (!result.AsyncWaitHandle.WaitOne(250))
                    return false;
                client.EndConnect(result);
                return true;
            }
        }
        catch
        {
            return false;
        }
    }
}
