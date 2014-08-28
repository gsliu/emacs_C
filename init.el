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


;;---------------------------ETAGS----------------------------------
(setq tags-file-name "~/src/linux/TAGS")
(global-set-key (kbd "C-1") 'tags-search)
(global-set-key (kbd "C-2") 'tags-loop-continue)
(global-set-key (kbd "C-3") 'tags-apropos)
;;-----------------------------END ETAGS---------------------------

;;------------------------
(setq ede-locate-setup-options
'(ede-locate-global
ede-locate-base))

;;(semanticdb-enable-gnu-global-databases 'c-mode)

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

;;(enable-visual-studio-bookmarks)
;;(custom-set-variables
  ;; custom-set-variables was added by Custom.
  ;; If you edit it by hand, you could mess it up, so be careful.
  ;; Your init file should contain only one such instance.
  ;; If there is more than one, they won't work right.
;; )



;;;--------------other window---------------
(global-set-key (kbd "C-<tab>") 'other-window)

;;----------------undo----------

(global-set-key (kbd "C-z") 'undo)

