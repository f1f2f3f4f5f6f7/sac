import { Component, inject, OnInit } from '@angular/core';
import { LoaderService } from '../loader.service';
import { delay } from 'rxjs';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

@Component({
  selector: 'app-loader',
  imports: [ProgressSpinnerModule],
  templateUrl: './loader.html',
  styleUrl: './loader.scss',
})
export class Loader {
  loader = inject(LoaderService).showLoader

}
