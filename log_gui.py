class LogGUI:
    def __init__(self, master):
        self.master = master
        master.title("BGOCRLG")

        self.label = Label(master, text="Battlegrounds log grabber")
        self.label.pack()

        self.greet_button = Button(master, text="Start", command=self.start)
        self.greet_button.pack()

        self.close_button = Button(master, text="Stop", command=self.stop)
        self.close_button.pack()

        master.after(1000, screenshot_loop)
        master.mainloop()

    def start(self):
        global RUN_FLAG, START_T
        print "Capturing kill feed..."
        START_T = time.time()
        RUN_FLAG = True

    def stop(self):
        global RUN_FLAG, IMAGE_COUNTER
        RUN_FLAG = False
        IMAGE_COUNTER = len(IMAGES)
        events = process_images()
        export_csv(events)
