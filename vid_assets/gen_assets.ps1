Add-Type -AssemblyName System.Drawing
$W = 1920; $H = 1012
$out = "D:\clawcode\vid_assets"
$S = [System.IO.File]::ReadAllLines("$out\strings.txt", [System.Text.Encoding]::UTF8)
$TITLE1 = $S[0]; $TITLE2 = $S[1]; $OV2 = $S[2]
$items = @($S[3], $S[4], $S[5])

function New-Canvas {
    $bmp = New-Object System.Drawing.Bitmap($W, $H, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    return @($bmp, $g)
}

function Get-RoundRect([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $r * 2
    $p.AddArc($x, $y, $d, $d, 180, 90)
    $p.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $p.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $p.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $p.CloseFigure()
    return $p
}

function Draw-CryingFace($g, [float]$cx, [float]$cy, [float]$r) {
    $face = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,255,202,40))
    $g.FillEllipse($face, $cx - $r, $cy - $r, 2*$r, 2*$r)
    $outline = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,230,160,20)), ([float]($r*0.06))
    $g.DrawEllipse($outline, $cx - $r, $cy - $r, 2*$r, 2*$r)
    $eyePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,60,40,10)), ([float]($r*0.10))
    $eyePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $eyePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $ew = $r*0.45
    $g.DrawArc($eyePen, $cx - $r*0.62, $cy - $r*0.30, $ew, $r*0.45, 200, 140)
    $g.DrawArc($eyePen, $cx + $r*0.17, $cy - $r*0.30, $ew, $r*0.45, 200, 140)
    $g.DrawArc($eyePen, $cx - $r*0.40, $cy + $r*0.35, $r*0.80, $r*0.55, 180, 180)
    $tear = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,79,195,247))
    $tx = $cx - $r*0.42; $ty = $cy + $r*0.05
    $tp = New-Object System.Drawing.Drawing2D.GraphicsPath
    $tp.AddEllipse($tx - $r*0.12, $ty, $r*0.24, $r*0.30)
    $g.FillPath($tear, $tp)
    $pts = @(
        (New-Object System.Drawing.PointF([float]$tx, [float]($ty - $r*0.22))),
        (New-Object System.Drawing.PointF([float]($tx - $r*0.12), [float]($ty + $r*0.10))),
        (New-Object System.Drawing.PointF([float]($tx + $r*0.12), [float]($ty + $r*0.10)))
    )
    $g.FillPolygon($tear, $pts)
}

function Draw-Bulb($g, [float]$cx, [float]$cy, [float]$r) {
    $rayPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,255,213,79)), ([float]($r*0.10))
    $rayPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $rayPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    for ($a = -90; $a -le 90; $a += 45) {
        $rad = $a * [Math]::PI / 180.0
        $x1 = $cx + [Math]::Cos($rad) * $r * 1.35
        $y1 = $cy + [Math]::Sin($rad) * $r * 1.35
        $x2 = $cx + [Math]::Cos($rad) * $r * 1.70
        $y2 = $cy + [Math]::Sin($rad) * $r * 1.70
        $g.DrawLine($rayPen, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
    }
    $glow = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,255,241,118))
    $g.FillEllipse($glow, $cx - $r, $cy - $r, 2*$r, 2*$r)
    $bo = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,251,192,45)), ([float]($r*0.07))
    $g.DrawEllipse($bo, $cx - $r, $cy - $r, 2*$r, 2*$r)
    $fp = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,245,124,0)), ([float]($r*0.06))
    $g.DrawLine($fp, [float]($cx - $r*0.25), [float]($cy + $r*0.15), [float]($cx - $r*0.10), [float]($cy - $r*0.10))
    $g.DrawLine($fp, [float]($cx - $r*0.10), [float]($cy - $r*0.10), [float]($cx + $r*0.10), [float]($cy - $r*0.10))
    $g.DrawLine($fp, [float]($cx + $r*0.10), [float]($cy - $r*0.10), [float]($cx + $r*0.25), [float]($cy + $r*0.15))
    $base = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,120,120,120))
    $g.FillRectangle($base, [float]($cx - $r*0.42), [float]($cy + $r*0.92), [float]($r*0.84), [float]($r*0.55))
    $bp = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,80,80,80)), ([float]($r*0.05))
    $g.DrawLine($bp, [float]($cx - $r*0.42), [float]($cy + $r*1.10), [float]($cx + $r*0.42), [float]($cy + $r*1.10))
    $g.DrawLine($bp, [float]($cx - $r*0.42), [float]($cy + $r*1.28), [float]($cx + $r*0.42), [float]($cy + $r*1.28))
}

$white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$pb = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(205,15,23,42))
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment = [System.Drawing.StringAlignment]::Center
$sf.LineAlignment = [System.Drawing.StringAlignment]::Center
$sfL = New-Object System.Drawing.StringFormat
$sfL.Alignment = [System.Drawing.StringAlignment]::Near
$sfL.LineAlignment = [System.Drawing.StringAlignment]::Center
$rect = New-Object System.Drawing.Rectangle(0,0,$W,$H)

# blue caption style (transparent bg) shared by all non-title-1 text
$fontTxt = New-Object System.Drawing.Font("Segoe UI", 25, [System.Drawing.FontStyle]::Bold)
$blueCol = [System.Drawing.Color]::FromArgb(255,21,101,192)
$shadowCol = [System.Drawing.Color]::FromArgb(175,0,0,0)
function Draw-TextShadow($g, $text, $font, $r, $fmt) {
    $sr = New-Object System.Drawing.RectangleF(([float]($r.X + 2.5)), ([float]($r.Y + 2.5)), $r.Width, $r.Height)
    $sb = New-Object System.Drawing.SolidBrush $shadowCol
    $g.DrawString($text, $font, $sb, $sr, $fmt)
    $bb = New-Object System.Drawing.SolidBrush $blueCol
    $g.DrawString($text, $font, $bb, $r, $fmt)
}

# ---------- TITLE 1 ----------
$c = New-Canvas; $bmp = $c[0]; $g = $c[1]
$grad = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, [System.Drawing.Color]::FromArgb(255,11,30,59), [System.Drawing.Color]::FromArgb(255,21,53,107), 90)
$g.FillRectangle($grad, $rect)
$gold = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,255,193,7))
$g.FillRectangle($gold, [float]($W/2 - 120), 320, 240, 8)
$fontTitle = New-Object System.Drawing.Font("Segoe UI", 68, [System.Drawing.FontStyle]::Bold)
$tr = New-Object System.Drawing.RectangleF(180, 380, ($W-360), 280)
$g.DrawString($TITLE1, $fontTitle, $white, $tr, $sf)
$bmp.Save("$out\title1.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

# ---------- TITLE 2 (full slide: green bg + bulb card + white title) ----------
$c = New-Canvas; $bmp = $c[0]; $g = $c[1]
$grad2 = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, [System.Drawing.Color]::FromArgb(255,4,46,38), [System.Drawing.Color]::FromArgb(255,13,94,68), 90)
$g.FillRectangle($grad2, $rect)
$bulb = [System.Drawing.Image]::FromFile("$out\bulb.png")
$cardW = 460; $cardH = 380; $cardX = ($W - $cardW)/2; $cardY = 110
$card = Get-RoundRect $cardX $cardY $cardW $cardH 30
$wbrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$g.FillPath($wbrush, $card)
$cardBorder = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,225,225,225)), 3
$g.DrawPath($cardBorder, $card)
$pad = 28; $iw = $cardW - 2*$pad; $ih = $cardH - 2*$pad
$scale = [Math]::Min($iw / $bulb.Width, $ih / $bulb.Height)
$dw = $bulb.Width * $scale; $dh = $bulb.Height * $scale
$bx = $cardX + ($cardW - $dw)/2; $by = $cardY + ($cardH - $dh)/2
$g.DrawImage($bulb, [float]$bx, [float]$by, [float]$dw, [float]$dh)
$bulb.Dispose()
$fontT2 = New-Object System.Drawing.Font("Segoe UI", 62, [System.Drawing.FontStyle]::Bold)
$tr2 = New-Object System.Drawing.RectangleF(180, 540, ($W-360), 200)
$g.DrawString($TITLE2, $fontT2, $white, $tr2, $sf)
$bmp.Save("$out\title2.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

# ---------- OVERLAY 2 (panel + cat circle + white caption) ----------
$c = New-Canvas; $bmp = $c[0]; $g = $c[1]
$g.Clear([System.Drawing.Color]::Transparent)
$cat = [System.Drawing.Image]::FromFile("$out\cat.jpg")
$cd = 170
$fontBody = New-Object System.Drawing.Font("Segoe UI", 36, [System.Drawing.FontStyle]::Bold)
# measure wrapped text so the panel hugs the content
$layout = New-Object System.Drawing.SizeF(720, 10000)
$measured = $g.MeasureString($OV2, $fontBody, $layout, $sfL)
$textW = [Math]::Ceiling($measured.Width); $textH = [Math]::Ceiling($measured.Height)
$leftPad = 34; $gap = 26; $rightPad = 40; $vpad = 28
$contentH = [Math]::Max($cd, $textH)
$panelH = $contentH + 2*$vpad
$panelW = $leftPad + $cd + $gap + $textW + $rightPad
$panelX = [int](($W - $panelW)/2)
$panelY = [int](958 - $panelH)
$panel = Get-RoundRect $panelX $panelY $panelW $panelH 28
$paleBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(252,232,245,233))
$paleBorder = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,102,187,106)), 3
$textGreen = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,27,134,66))
$g.FillPath($paleBrush, $panel)
$g.DrawPath($paleBorder, $panel)
$ccx = $panelX + $leftPad + $cd/2; $ccy = $panelY + $panelH/2
$clip = New-Object System.Drawing.Drawing2D.GraphicsPath
$clip.AddEllipse([float]($ccx - $cd/2), [float]($ccy - $cd/2), [float]$cd, [float]$cd)
$g.SetClip($clip)
$g.DrawImage($cat, [float]($ccx - $cd/2), [float]($ccy - $cd/2), [float]$cd, [float]$cd)
$g.ResetClip()
$ring = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,102,187,106)), 5
$g.DrawEllipse($ring, [float]($ccx - $cd/2), [float]($ccy - $cd/2), [float]$cd, [float]$cd)
$cat.Dispose()
$txtX = $panelX + $leftPad + $cd + $gap
$txtRect = New-Object System.Drawing.RectangleF([float]$txtX, [float]($panelY + $vpad), [float]($textW + 6), [float]$contentH)
$g.DrawString($OV2, $fontBody, $textGreen, $txtRect, $sfL)
$bmp.Save("$out\overlay2.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

# ---------- P5 cumulative lists (green panel, white text, LEFT half) ----------
$fontBullet = New-Object System.Drawing.Font("Segoe UI", 34, [System.Drawing.FontStyle]::Bold)
$fontNum = New-Object System.Drawing.Font("Segoe UI", 27, [System.Drawing.FontStyle]::Bold)
$paleList = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(252,232,245,233))
$paleBorderL = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255,102,187,106)), 3
$textGreenL = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,27,134,66))
$badgeGreen = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,30,158,74))
$numWhite = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$sfC = New-Object System.Drawing.StringFormat
$sfC.Alignment = [System.Drawing.StringAlignment]::Center
$sfC.LineAlignment = [System.Drawing.StringAlignment]::Center
$sfTop = New-Object System.Drawing.StringFormat
$sfTop.Alignment = [System.Drawing.StringAlignment]::Near
$sfTop.LineAlignment = [System.Drawing.StringAlignment]::Near
$pX = 50; $pW = 880; $padX = 30; $padY = 30; $badge = 56; $gapBadge = 22; $rowGap = 18
$textW = $pW - $padX - $badge - $gapBadge - $padX
# measure wrapped height of each item using a temp graphics
$mc = New-Canvas; $mbmp = $mc[0]; $mg = $mc[1]
$layoutL = New-Object System.Drawing.SizeF([float]$textW, 10000)
$heights = @()
foreach ($it in $items) {
    $m = $mg.MeasureString($it, $fontBullet, $layoutL, $sfTop)
    $heights += [int][Math]::Max($badge, [Math]::Ceiling($m.Height))
}
$mg.Dispose(); $mbmp.Dispose()
$fullH = $padY*2 + ($heights[0] + $heights[1] + $heights[2]) + $rowGap*2
$pYfixed = [int](($H - $fullH)/2)
for ($n = 1; $n -le 3; $n++) {
    $c = New-Canvas; $bmp = $c[0]; $g = $c[1]
    $g.Clear([System.Drawing.Color]::Transparent)
    $sumN = 0; for ($k = 0; $k -lt $n; $k++) { $sumN += $heights[$k] }
    $pH = $padY*2 + $sumN + $rowGap*([Math]::Max(0, $n-1))
    $panel = Get-RoundRect $pX $pYfixed $pW $pH 28
    $g.FillPath($paleList, $panel)
    $g.DrawPath($paleBorderL, $panel)
    $run = $pYfixed + $padY
    for ($i = 0; $i -lt $n; $i++) {
        $g.FillEllipse($badgeGreen, [float]($pX + $padX), [float]($run - 2), [float]$badge, [float]$badge)
        $numRect = New-Object System.Drawing.RectangleF([float]($pX + $padX), [float]($run - 2), [float]$badge, [float]$badge)
        $g.DrawString(($i + 1).ToString(), $fontNum, $numWhite, $numRect, $sfC)
        $itRect = New-Object System.Drawing.RectangleF([float]($pX + $padX + $badge + $gapBadge), [float]$run, [float]($textW + 6), [float]$heights[$i])
        $g.DrawString($items[$i], $fontBullet, $textGreenL, $itRect, $sfTop)
        $run += $heights[$i] + $rowGap
    }
    $bmp.Save("$out\list$n.png", [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
}

Get-ChildItem $out -Filter *.png | Select-Object Name, Length | Format-Table -AutoSize
Write-Output "DONE"
