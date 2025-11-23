using System;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
using System.Text;

namespace FileMappingApp
{
    public class ModeSelectionForm : Form
    {
        private Button writerButton;
        private Button readerButton;
        private Label infoLabel;
        private System.Windows.Forms.Timer checkTimer;
        private Mutex appMutex;

        public ModeSelectionForm()
        {
            InitializeUI();
            SetupTimer();
        }

        private void InitializeUI()
        {
            this.Text = "Выберите режим работы";
            this.Size = new Size(400, 200);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.MaximizeBox = false;
            this.MinimizeBox = false;

            // Основной контейнер
            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 2,
                ColumnCount = 1,
                Padding = new Padding(10)
            };
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 70));
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 30));

            // Информационная метка
            infoLabel = new Label
            {
                Text = "Выберите режим запуска приложения:",
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Fill,
                Font = new Font("Arial", 10)
            };
            mainPanel.Controls.Add(infoLabel, 0, 0);

            // Панель для кнопок (внизу)
            var buttonPanel = new Panel
            {
                Dock = DockStyle.Fill
            };

            writerButton = new Button
            {
                Text = "Писатель",
                Size = new Size(120, 40),
                Font = new Font("Arial", 10),
                Enabled = true,
                Anchor = AnchorStyles.None
            };

            readerButton = new Button
            {
                Text = "Читатель",
                Size = new Size(120, 40),
                Font = new Font("Arial", 10),
                Enabled = false,
                Anchor = AnchorStyles.None
            };

            // Центрируем кнопки
            writerButton.Location = new Point(
                buttonPanel.Width / 2 - writerButton.Width - 10,
                buttonPanel.Height / 2 - writerButton.Height / 2);

            readerButton.Location = new Point(
                buttonPanel.Width / 2 + 10,
                buttonPanel.Height / 2 - readerButton.Height / 2);

            // Обработчики событий
            writerButton.Click += WriterButton_Click;
            readerButton.Click += (s, e) => new MainForm(false).Show();

            buttonPanel.Controls.Add(writerButton);
            buttonPanel.Controls.Add(readerButton);
            mainPanel.Controls.Add(buttonPanel, 0, 1);

            this.Controls.Add(mainPanel);
        }

        private void SetupTimer()
        {
            checkTimer = new System.Windows.Forms.Timer { Interval = 1000 };
            checkTimer.Tick += CheckWriterStatus;
            this.Load += (s, e) => checkTimer.Start();
            this.FormClosing += (s, e) => checkTimer.Stop();
        }

        private void WriterButton_Click(object sender, EventArgs e)
        {
            try
            {
                bool mutexCreated;
                appMutex = new Mutex(true, "FileMappingAppWriterMutex", out mutexCreated);

                if (!mutexCreated)
                {
                    MessageBox.Show("Писатель уже запущен в другом экземпляре программы");
                    return;
                }

                var writerForm = new MainForm(true);
                writerForm.FormClosed += (s2, e2) =>
                {
                    appMutex?.ReleaseMutex();
                    appMutex?.Dispose();
                    appMutex = null;
                    UpdateUI(false);
                };

                writerForm.Show();
                UpdateUI(true);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка запуска писателя: {ex.Message}");
            }
        }

        private void CheckWriterStatus(object sender, EventArgs e)
        {
            bool writerRunning = false;
            try
            {
                writerRunning = Mutex.TryOpenExisting("FileMappingAppWriterMutex", out _);
            }
            catch { }

            UpdateUI(writerRunning);
        }

        private void UpdateUI(bool writerRunning)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new Action<bool>(UpdateUI), writerRunning);
                return;
            }

            writerButton.Enabled = !writerRunning;
            readerButton.Enabled = writerRunning;
            infoLabel.Text = writerRunning
                ? "Писатель запущен (можно запускать читателей)"
                : "Выберите режим запуска приложения:";
        }
    }

    public class MainForm : Form
    {
        private MemoryMappedFile mmf;
        private System.Windows.Forms.Timer updateTimer;
        private TextBox contentTextBox;
        private Label statusLabel;
        private readonly bool isWriterMode;
        private const string MappingName = "SharedFileMapping";
        private const string FileName = "sharedfile.bin";
        private const int MaxFileSize = 2048;

        public MainForm(bool writerMode)
        {
            isWriterMode = writerMode;
            InitializeUI();
            InitializeMode();
        }

        private void InitializeUI()
        {
            this.Text = isWriterMode ? "Писатель" : $"Читатель ({DateTime.Now:HH:mm:ss})";
            this.Size = new Size(600, 400);

            statusLabel = new Label
            {
                Dock = DockStyle.Bottom,
                Height = 30,
                TextAlign = ContentAlignment.MiddleLeft,
                BackColor = Color.LightGray
            };

            contentTextBox = new TextBox
            {
                Multiline = true,
                Dock = DockStyle.Fill,
                ScrollBars = ScrollBars.Vertical,
                Font = new Font("Arial", 12),
                WordWrap = true
            };

            if (isWriterMode)
            {
                contentTextBox.TextChanged += (s, e) => UpdateSharedFile(contentTextBox.Text);
            }

            this.Controls.Add(contentTextBox);
            this.Controls.Add(statusLabel);
            this.FormClosing += (s, e) => CleanupResources();
        }

        private void InitializeMode()
        {
            try
            {
                if (isWriterMode)
                {
                    using (var fs = new FileStream(FileName, FileMode.Create))
                    {
                        fs.Write(new byte[MaxFileSize], 0, MaxFileSize);
                    }
                    mmf = MemoryMappedFile.CreateFromFile(FileName, FileMode.Open, MappingName, MaxFileSize);
                    contentTextBox.Text = "Введите текст здесь...";
                    statusLabel.Text = "Режим Писателя - вводите текст в поле выше";
                }
                else
                {
                    mmf = MemoryMappedFile.OpenExisting(MappingName);
                    contentTextBox.ReadOnly = true;
                    contentTextBox.BackColor = Color.LightYellow;
                    updateTimer = new System.Windows.Forms.Timer { Interval = 300 };
                    updateTimer.Tick += (s, e) => CheckForUpdates();
                    updateTimer.Start();
                    CheckForUpdates();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка инициализации: {ex.Message}");
                this.Close();
            }
        }

        private void UpdateSharedFile(string text)
        {
            try
            {
                using (var accessor = mmf.CreateViewAccessor())
                {
                    byte[] data = Encoding.UTF8.GetBytes(text);
                    int length = Math.Min(data.Length, MaxFileSize - 1);
                    accessor.WriteArray(0, data, 0, length);
                    accessor.Write(length, (byte)0);
                    statusLabel.Text = $"Обновлено: {DateTime.Now:HH:mm:ss}";
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка обновления: {ex.Message}");
            }
        }

        private void CheckForUpdates()
        {
            try
            {
                using (var accessor = mmf.CreateViewAccessor())
                {
                    byte[] data = new byte[MaxFileSize];
                    accessor.ReadArray(0, data, 0, data.Length);
                    string content = Encoding.UTF8.GetString(data).TrimEnd('\0');

                    if (content != contentTextBox.Text)
                    {
                        contentTextBox.Text = content;
                        statusLabel.Text = $"Получено: {DateTime.Now:HH:mm:ss}";
                    }
                }
            }
            catch (Exception ex)
            {
                updateTimer?.Stop();
                MessageBox.Show($"Ошибка чтения: {ex.Message}");
                this.Close();
            }
        }

        private void CleanupResources()
        {
            updateTimer?.Stop();
            mmf?.Dispose();
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ModeSelectionForm());
        }
    }
}