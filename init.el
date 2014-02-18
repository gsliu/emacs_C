(setq x-select-enable-clipboard t)      ; support copy and paste between emacs and X window
(tool-bar-mode -1)                     ; disable tool bar, must be -1, nil will caust toggle
(scroll-bar-mode -1)
(menu-bar-mode -1)

(add-to-list 'load-path "~/.emacs.d/elisp/color-theme-6.6.0")
(add-to-list 'load-path "~/.emacs.d/elisp")
(add-to-list 'load-path "~/.emacs.d/Pymacs")
(add-to-list 'load-path "~/.emacs.d/site-lisp")


(require 'color-theme)
(color-theme-initialize)
(color-theme-gray30)
(color-theme-simple-1)
(global-set-key (kbd "C-;") 'yp-goto-next-line)
(global-set-key (kbd "C-M-;") 'yp-goto-prev-line)
(global-set-key (kbd "C-x n") 'get-buffer-create)
(defun yp-goto-next-line ()
"document"
(interactive)
(end-of-line)
(newline-and-indent))
(defun yp-goto-prev-line ()
"document"
(interactive)
(beginning-of-line)
(newline-and-indent)
(beginning-of-line 0)
(indent-according-to-mode))

(setq-default make-backup-files nil)
(global-font-lock-mode 't)
(setq inhibit-startup-message t)
(fset 'yes-or-no-p 'y-or-n-p)

;;hide region
(require 'hide-region)
(global-set-key (kbd "C-c t") '(lambda () (interactive) (hide-region-hide) (deactivate-mark)))
(global-set-key (kbd "C-c y") 'hide-region-unhide-below)
(global-set-key (kbd "M-T") 'hide-region-toggle)

;; hide lines
;; (require 'hide-lines)
(autoload 'hide-lines "hide-lines" "Hide lines based on a regexp" t)
(global-set-key (kbd "C-c g") 'hide-lines)
(global-set-key (kbd "C-c h") 'show-all-invisible)

;; highlight symbol
(require 'highlight-symbol)
(global-set-key (kbd "M-n") 'highlight-symbol-next)
(global-set-key (kbd "M-p") 'highlight-symbol-prev)
(global-set-key (kbd "C-c j") 'highlight-symbol-at-point)

;; set directory must before load ido, or it only save .ido.last
;; to that directory, but can not read when start up
(setq ido-save-directory-list-file "~/.emacs.d/.ido.last")
(require 'ido)
(ido-mode t)
(ido-everywhere 1)
(setq ido-enable-tramp-completion nil)
(global-set-key (kbd "<f12>") 'ido-switch-buffer)
(defun yp-ido-mode-init ()
"document"
(interactive)
(define-key ido-completion-map (kbd "<f12>") 'ido-next-match)
(define-key ido-completion-map (kbd "<f11>") 'ido-prev-match))
(add-hook 'ido-setup-hook 'yp-ido-mode-init)
;;--------------------------CEDET-----------------------------------------
;;Load CEDET.
;; See cedet/common/cedet.info for configuration details.
(load-file "~/.emacs.d/cedet-1.1/common/cedet.el")


;; Enable EDE (Project Management) features
(global-ede-mode 1)

;; Enable EDE for a pre-existing C++ project
;; (ede-cpp-root-project "NAME" :file "~/myproject/Makefile")


;; Enabling Semantic (code-parsing, smart completion) features
;; Select one of the following:

;; * This enables the database and idle reparse engines
(semantic-load-enable-minimum-features)

;; * This enables some tools useful for coding, such as summary mode
;;   imenu support, and the semantic navigator
;;(semantic-load-enable-code-helpers)

;; * This enables even more coding tools such as intellisense mode
;;   decoration mode, and stickyfunc mode (plus regular code helpers)
;; (semantic-load-enable-gaudy-code-helpers)

;; * This enables the use of Exuberent ctags if you have it installed.
;;   If you use C++ templates or boost, you should NOT enable it.
;; (semantic-load-enable-all-exuberent-ctags-support)
;;   Or, use one of these two types of support.
;;   Add support for new languges only via ctags.
;; (semantic-load-enable-primary-exuberent-ctags-support)
;;   Add support for using ctags as a backup parser.
;; (semantic-load-enable-secondary-exuberent-ctags-support)

;; Enable SRecode (Template management) minor-mode.
;; (global-srecode-minor-mode 1)
;;--------------------------END CEDET-----------------------------------------

;;--------------------------global-----------------------------------------
(autoload 'gtags-mode "gtags" "" t)

(add-hook 'c-mode-hook
'(lambda ()
(gtags-mode 1)))

(add-hook 'c++-mode-hook
'(lambda ()
(gtags-mode 1)))

(add-hook 'asm-mode-hook
'(lambda ()
(gtags-mode 1)))

(setq auto-save-hook nil)
(global-set-key "\C-c/" 'semantic-ia-fast-jump)
(setq default-indent-tabs-mode nil)
(setq default-tab-width 4)


(gtags-mode 1) ;; 好像不在.emacs中使能gtags-mode下面的函数就找不到。
(define-prefix-command 'yp-gtags-map) ;; 和下一句话合起来定义一个自己的快捷键头（C-xg）。
(global-set-key "\C-xg" 'yp-gtags-map)
(define-key gtags-mode-map "\C-xgv" 'gtags-visit-rootdir)  ;; 选择搜索的根目录。
(define-key gtags-mode-map "\C-xgt" 'gtags-find-tag)  ;; 找函数定义
;;(define-key gtags-mode-map "\M-." 'gtags-find-tag-from-here)  ;; 找函数定义
(define-key gtags-mode-map "\C-xgo" 'gtags-find-tag-other-window)  ;; 打开一个新窗口找函数定义
(define-key gtags-mode-map "\C-xgr" 'gtags-find-rtag)  ;; 找函数的调用
(define-key gtags-mode-map "\C-xgs" 'gtags-find-symbol)  ;; 搜索符号，也就是变量的定义和调用
(define-key gtags-mode-map "\C-xgp" 'gtags-find-pattern)  ;; 似乎和下面两个一样，都是在项目中进行字符串搜索，不知道有啥区别，不会使。
(define-key gtags-mode-map "\C-xgg" 'gtags-find-with-grep)
(define-key gtags-mode-map "\C-xgi" 'gtags-find-with-idutils)
(define-key gtags-mode-map "\C-xgf" 'gtags-find-file)  ;; 在项目中搜索文件。
(define-key gtags-mode-map "\C-xga" 'gtags-parse-file)  ;; 分析指定文件（基本就是找到所有能找到的定义），列在emacs中。
(define-key gtags-mode-map "\C-xgb" 'yp-gtags-append)  ;; 更新项目的tag文件，该函数在后面定义。
(defun yp-gtags-append ()
(interactive)
(if gtags-mode
(progn
(message "start to global -u")
(start-process "gtags-name" "*gtags-var*" "global" "-u"))))
;;--------------------------END global-----------------------------------------

;;------------------------
(setq ede-locate-setup-options
'(ede-locate-global
ede-locate-base))

(semanticdb-enable-gnu-global-databases 'c-mode)

;;---------------折叠花括号-----------
(add-hook 'c-mode-common-hook   'hs-minor-mode)
(add-hook 'emacs-lisp-mode-hook 'hs-minor-mode)
(add-hook 'java-mode-hook       'hs-minor-mode)
(add-hook 'lisp-mode-hook       'hs-minor-mode)
(add-hook 'perl-mode-hook       'hs-minor-mode)
(add-hook 'sh-mode-hook         'hs-minor-mode)


(global-set-key (kbd "<f1> C-h") 'hs-hide-block)
(global-set-key (kbd "<f1> C-s") 'hs-show-block)
(global-set-key (kbd "<f1> C-M-h") 'hs-hide-all)
(global-set-key (kbd "<f1> C-M-s") 'hs-show-all)
(global-set-key (kbd "<f1> C-l") 'hs-hide-level)
(global-set-key (kbd "<f1> C-c") 'hs-toggle-hiding)
;;---------------END 折叠花括号-----------

;;------Python Mode-----------
;;#(autoload 'pymacs-apply "pymacs")
;;#(autoload 'pymacs-call "pymacs")
;;#(autoload 'pymacs-eval "pymacs" nil t)
;;#(autoload 'pymacs-exec "pymacs" nil t)
;;#(autoload 'pymacs-load "pymacs" nil t)
;;#
;;#(autoload 'python-mode "python-mode" "Python Mode." t)
;;#(add-to-list 'auto-mode-alist '("\\.py\\'" . python-mode))
;;#(add-to-list 'interpreter-mode-alist '("python" . python-mode))
;;#
;;#(require 'pycomplete)
;;#
;;------------Change the font----------------
;;(defun try-set-font (font-list font-size)
;;(defun font-exists (font-name)
;;(if (null (x-list-fonts font-name)) nil t))
;;(when font-list
;;(let ((font-name (car font-list)))
;;(if (font-exists font-name)
;;  (set-default-font (concat font-name "-"
;;    (number-to-string font-size)))
;;  (try-set-font (cdr font-list) font-size)))))
;;(try-set-font '("Monaco" "DejaVu Sans Mono" "Courier New") 15)
;;(set-fontset-font (frame-parameter nil 'font)
;;                   'japanese-jisx0208
;;                   '("VL Gothic" . "unicode-bmp"))


;;(let ((font-name (car font-list)))
;;(if (font-exists font-name)
;;  (set-default-font (concat font-name "-"
;;    (number-to-string font-size)))
;;  (try-set-font (cdr font-list) font-size)))))
;;(try-set-font '("Monaco" "DejaVu Sans Mono" "Courier New") 15)
;;(set-fontset-font (frame-parameter nil 'font)
;;                   'japanese-jisx0208
;;                   '("VL Gothic" . "unicode-bmp"))
;;(set-default-font "Inconsolata 12")
;;------------End---------------------------
(custom-set-faces
  ;; custom-set-faces was added by Custom.
  ;; If you edit it by hand, you could mess it up, so be careful.
  ;; Your init file should contain only one such instance.
  ;; If there is more than one, they won't work right.
 '(default ((t (:inherit nil :stipple nil :background "black" :foreground "white" :inverse-video nil :box nil :strike-through nil :overline nil :underline nil :slant normal :weight normal :height 143 :width normal :foundry "unknown" :family "DejaVu Sans")))))

;;(autoload 'python-mode "python-mode" "Python Mode." t)
;;(add-to-list 'auto-mode-alist '("\\.py\\'" . python-mode))
;;(add-to-list 'interpreter-mode-alist '("python" . python-mode))
;;
;;(require 'pycomplete)
;;------END Python Mode-----------
;;
(autoload 'markdown-mode "markdown-mode.el"
    "Major mode for editing Markdown files" t) 
(setq auto-mode-alist 
    (cons '("\\.md" . markdown-mode) auto-mode-alist))

;;------Add iBus Support------
;;(require 'ibus)
;;(add-hook 'after-init-hook 'ibus-mode-on)

;; C-SPC は Set Mark に使う
;;(ibus-define-common-key ?\C-\s nil)
;; C-/ は Undo に使う
;;(ibus-define-common-key ?\C-/ nil)
;; IBusの状態によってカーソル色を変化させる
;;(setq ibus-cursor-color '("red" "white" "limegreen"))
;; C-j で半角英数モードをトグルする
;;(ibus-define-common-key ?\C-j t)
;;-------- End ----------

;;------- Disable Mark Set ---------------
(define-key global-map "\C-@" 'set-mark-command)
(global-set-key [?\S- ] 'set-mark-command) 
;;-----------End----------------

;;------- ADD linum ------------

(add-to-list 'load-path "/usr/share/emacs/site-lisp")
(require 'linum)
(global-linum-mode t)

;;-------- End ----------------


;;----------Set up emacs mode----------
;;(ibus-mode t)

;;----------End--------------
;;----------cscope------------
(require 'xcscope)

(define-key global-map [(control f3)]  'cscope-set-initial-directory)
(define-key global-map [(control f4)]  'cscope-unset-initial-directory)
(define-key global-map [(control f5)]  'cscope-find-this-symbol)
(define-key global-map [(control f6)]  'cscope-find-global-definition)
(define-key global-map [(control f7)]  'cscope-find-global-definition-no-prompting)
(define-key global-map [(control f8)]  'cscope-pop-mark)
(define-key global-map [(control f9)]  'cscope-next-symbol)
(define-key global-map [(control f10)] 'cscope-next-file)
(define-key global-map [(control f11)] 'cscope-prev-symbol)
(define-key global-map [(control f12)] 'cscope-prev-file)
(define-key global-map [(meta f9)]     'cscope-display-buffer)
(define-key global-map [(meta f10)]    'cscope-display-buffer-toggle)

;;---------------default max screen------------
(global-set-key [f11] 'my-fullscreen)

;全屏
(defun my-fullscreen ()
  (interactive)
  (x-send-client-message
   nil 0 nil "_NET_WM_STATE" 32
   '(2 "_NET_WM_STATE_FULLSCREEN" 0))
)

;最大化
(defun my-maximized ()
  (interactive)
  (x-send-client-message
   nil 0 nil "_NET_WM_STATE" 32
   '(2 "_NET_WM_STATE_MAXIMIZED_HORZ" 0))
  (x-send-client-message
   nil 0 nil "_NET_WM_STATE" 32
   '(2 "_NET_WM_STATE_MAXIMIZED_VERT" 0))
)
;启动时最大化
(my-maximized)

;;-----------------enable bookmark default

(enable-visual-studio-bookmarks)
(custom-set-variables
  ;; custom-set-variables was added by Custom.
  ;; If you edit it by hand, you could mess it up, so be careful.
  ;; Your init file should contain only one such instance.
  ;; If there is more than one, they won't work right.
 )



;;;--------------other window---------------
(global-set-key (kbd "C-<tab>") 'other-window)

;;----------------undo----------

(global-set-key (kbd "C-z") 'undo)

