pub fn clean(&mut self) {
        self.pool_ptr = 0;
        self.rndptr = 0;
        self.pool = [0; 32];
        self.ira = [0; RAND_NK];
        self.borrow = 0;
    }
