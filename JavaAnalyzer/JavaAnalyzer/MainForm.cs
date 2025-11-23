using Antlr4.Runtime;
using JavaAnalyzer;
using System;
using System.IO;
using System.Windows.Forms;
using Antlr4.Runtime.Tree;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Linq;

namespace JavaAnalyzer
{
    public partial class MainForm : Form
    {
        string filePath = "";
        private string _codeContent = string.Empty;
        private List<string> _codeLines = new List<string>();

        public MainForm()
        {
            InitializeComponent();
            InitializeDataGridViewColumns();
            ConfigureDataGridViewLayout();
            LoadTokensAndTree();
        }

        private void InitializeDataGridViewColumns()
        {
            tokensDataGridView.Columns.Clear();

            // Настраиваем колонки таблицы
            tokensDataGridView.Columns.Add("Type", "Тип токена");
            tokensDataGridView.Columns.Add("Line", "Строка");
            tokensDataGridView.Columns.Add("Position", "Позиция");
            tokensDataGridView.Columns.Add("Text", "Текст");

            // Настраиваем ширину колонок
            tokensDataGridView.Columns["Type"].Width = 150;
            tokensDataGridView.Columns["Line"].Width = 60;
            tokensDataGridView.Columns["Position"].Width = 70;
            tokensDataGridView.Columns["Text"].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
        }

        private void ConfigureDataGridViewLayout()
        {
            // Настраиваем внешний вид таблицы
            tokensDataGridView.Dock = DockStyle.Fill;
            tokensDataGridView.ReadOnly = true;
            tokensDataGridView.RowHeadersVisible = false;
            tokensDataGridView.ScrollBars = ScrollBars.Vertical;
            tokensDataGridView.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            tokensDataGridView.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.None;
            tokensDataGridView.AllowUserToResizeColumns = false;
            tokensDataGridView.AllowUserToResizeRows = false;
        }

        private void UpdateButton_Click(object sender, EventArgs e)
        {
            LoadTokensAndTree();
        }

        private void LoadTokensAndTree()
        {
            try
            {
                _codeContent = codeTextBox.Text;
                _codeLines = _codeContent.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None).ToList();

                var inputStream = new AntlrInputStream(_codeContent);
                var lexer = new JavaLexer(inputStream);
                var tokenStream = new CommonTokenStream(lexer);

                var parser = new JavaParser(tokenStream);
                var errorListener = new ErrorListener();
                parser.AddErrorListener(errorListener);

                tokenStream.Fill();
                tokensDataGridView.Rows.Clear();

                foreach (var token in tokenStream.GetTokens())
                {
                    if (token.Type == JavaLexer.Eof || token.Type == JavaLexer.WS)
                        continue;

                    // Получаем номер строки и позицию
                    int line = token.Line;
                    int position = token.Column + 1; // ANTLR использует 0-based позиции

                    tokensDataGridView.Rows.Add(
                        lexer.Vocabulary.GetSymbolicName(token.Type),
                        line,
                        position,
                        token.Text);
                }

                var tree = parser.compilationUnit();
                if (errorListener.Errors.Count > 0)
                {
                    errorsTextBox.Text = string.Join(Environment.NewLine, errorListener.Errors);
                    treeView.Nodes.Clear();
                    return;
                }
                else if (codeTextBox.Text.Length > 0 && errorListener.Errors.Count == 0)
                {
                    errorsTextBox.Text = "Синтаксических ошибок не обнаружено.";
                }

                DisplayParseTree(tree, parser);
            }
            catch (Exception ex)
            {
                errorsTextBox.Text = $"Ошибка при обработке файла: {ex.Message}";
            }
        }

        private void DisplayParseTree(IParseTree tree, JavaParser parser)
        {
            if (treeView.InvokeRequired)
            {
                treeView.Invoke(new Action(() => DisplayParseTree(tree, parser)));
                return;
            }

            treeView.BeginUpdate();
            try
            {
                treeView.Nodes.Clear();
                AddTreeNodes(treeView.Nodes, tree, parser);
            }
            finally
            {
                treeView.EndUpdate();
            }
        }

        private void AddTreeNodes(TreeNodeCollection nodes, IParseTree tree, JavaParser parser)
        {
            string nodeText;
            int startIndex = -1;
            int stopIndex = -1;

            if (tree is ITerminalNode terminal)
            {
                nodeText = $"{terminal.Symbol.Text} ({parser.Vocabulary.GetSymbolicName(terminal.Symbol.Type)})";
                startIndex = terminal.Symbol.StartIndex;
                stopIndex = terminal.Symbol.StopIndex;
            }
            else if (tree is ParserRuleContext rule)
            {
                nodeText = parser.RuleNames[rule.RuleIndex];
                startIndex = rule.Start.StartIndex;
                stopIndex = rule.Stop?.StopIndex ?? rule.Start.StopIndex;
            }
            else
            {
                nodeText = "Unknown";
            }

            var node = nodes.Add(nodeText);
            node.Tag = new Tuple<int, int>(startIndex, stopIndex);

            for (int i = 0; i < tree.ChildCount; i++)
            {
                AddTreeNodes(node.Nodes, tree.GetChild(i), parser);
            }
        }

        private void treeView_AfterSelect(object sender, TreeViewEventArgs e)
        {
            if (e.Node?.Tag is Tuple<int, int> positions)
            {
                int start = positions.Item1;
                int end = positions.Item2;

                if (start >= 0 && end >= 0 && end >= start)
                {
                    codeTextBox.BeginInvoke((Action)(() =>
                    {
                        codeTextBox.SelectionStart = start;
                        codeTextBox.SelectionLength = end - start + 1;
                        codeTextBox.ScrollToCaret();
                        codeTextBox.Focus();
                    }));
                }
            }
        }

        private void button1_Click(object sender, EventArgs e)
        {
            try
            {
                using (var ofd = new OpenFileDialog())
                {
                    ofd.Filter = "Java files (*.java)|*.java|All files (*.*)|*.*";
                    if (ofd.ShowDialog() == DialogResult.OK)
                    {
                        filePath = ofd.FileName;
                        codeTextBox.Text = File.ReadAllText(filePath);
                        LoadTokensAndTree();
                    }
                }
            }
            catch (Exception ex)
            {
                errorsTextBox.Text = $"Ошибка загрузки: {ex.Message}";
            }
        }

        private void ExitButton_Click(object sender, EventArgs e) => Application.Exit();
    }

    public class ErrorListener : BaseErrorListener
    {
        public List<string> Errors { get; } = new List<string>();

        public override void SyntaxError(TextWriter output, IRecognizer recognizer,
            IToken offendingSymbol, int line, int charPositionInLine,
            string msg, RecognitionException e)
        {
            Errors.Add($"Строка {line}:{charPositionInLine + 1} - {msg}");
        }
    }
}