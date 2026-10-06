using System;
using System.Diagnostics;
using System.Windows.Forms;

internal static class NeuroLyticsStop
{
    [STAThread]
    private static void Main()
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = "/c for /f \"tokens=5\" %P in ('netstat -ano ^| findstr \":5000\" ^| findstr \"LISTENING\"') do taskkill /PID %P /F",
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using (var p = Process.Start(psi))
            {
                if (p != null) p.WaitForExit(5000);
            }
            MessageBox.Show("NeuroLytics server stop request completed.", "NeuroLytics", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "NeuroLytics", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
